import gurobipy as gp
from gurobipy import GRB


import parameters
param = parameters.make_parameters(num_cert=10, num_cont=5, num_scen=5, num_fixed=5)

gap = 0.01
max_time = 60

def discrete(p=param['Discrete'], gap=gap, max_time=max_time):
    output = {'runtime':'infeasible', 'status':'infeasible', 'var':'infeasible',
              'obj':'infeasible', 'results':'infeasible',  'gantt':'infeasible',
              'prop_gantt':'infeasible', 'dist_completed':'infeasible', 'param':p,
              'gap':'infeasible'}

    try:
        # Create a new model
        m = gp.Model("Discrete")
    
        # Create variables
        dvX = [(j,m,k) for j in p['F'] for m in p['M'] for k in p['K']]
        dvY = [(j,m,k,s) for j in p['NF'] for m in p['M'] for k in p['K'] for s in p['S']]
        print(len(dvY))
        
        x = m.addVars(dvX, vtype=GRB.BINARY, name='x')
        y = m.addVars(dvY, vtype=GRB.BINARY, name='y')

   
        m.setObjective(gp.quicksum([
                            gp.quicksum([p['p_jmk'][(j,m,k)] * x[j,m,k] for j in p['F']]) + 
                            gp.quicksum([p['q_s'][s] * p['p_jmk'][(j,m,k)] * y[(j,m,k,s)]
                                         for s in p['S'] for j in p['NF']])
                            for m in p['M'] for k in p['K']
                            ]),
                sense=GRB.MINIMIZE)
    
        m.addConstrs((gp.quicksum([x[(j,m,k)] for m in p['M'] for k in p['K']]) == 1
                      for j in p['F']), name='assignmentX')

        m.addConstrs((gp.quicksum([y[(j,m,k,s)] for m in p['M'] for k in p['K']]) == 1
                      for j in p['NF'] for s in p['S'] if p['b_js'][j][s] == 1),
                     name='assignmentY')
        
        m.addConstrs((gp.quicksum([x[(j,m,k)] for j in p['F']]) +
                      gp.quicksum([y[(j,m,k,s)] for j in p['NF']]) <= 1
                      for m in p['M'] for k in p['K'] for s in p['S']),
                      name='resource')
        
        m.addConstrs((x[(j,m,k)] == 0 for j in p['F'] for m in p['M'] for k in p['K'] 
                      if k <= p['w_jm'][(j,m)]-1),
                     name='earliestX')

        m.addConstrs((y[(j,m,k,s)] == 0 for j in p['NF'] for m in p['M']
                     for s in p['S'] for k in p['K'] if k <= p['w_jm'][(j,m)]-1),
                     name='earliestY')      
        
        m.addConstrs((gp.quicksum([x[(a,m,k-u)] for a in p['F']]) +
                      gp.quicksum([y[(a,m,k-u,s)] for a in p['NF']]) <= 1 - x[(j,m,k)]
                     for j in p['F'] for m in p['M'] for s in p['S']
                     for u in [i for i in range(1,p['w_jm'][(j,m)])]
                     for k in p['K'] if k >= p['w_jm'][(j,m)]-1),
                     name='noOverLapX')
        
        m.addConstrs((gp.quicksum([x[(a,m,k-u)] for a in p['F']]) +
                      gp.quicksum([y[(a,m,k-u,s)] for a in p['NF']])<= 1 - y[(j,m,k,s)]
                     for j in p['NF'] for m in p['M'] for s in p['S']
                     for u in [i for i in range(1,p['w_jm'][(j,m)])]
                     for k in p['K'] if k >= p['w_jm'][(j,m)]-1),
                     name='noOverLapY')

        # Optimize model
        m.Params.mipgap = gap
        m.Params.timelimit = max_time
        m.optimize()
        
        runtime = m.runtime
        status = m.Status
        mipGap = m.MIPGap
        variables = [v.varName for v in m.getVars() if v.x  > 0]
        assignment = [v[2:-1].split(',') for v in variables]
        objective = m.objVal
        
        output = {'runtime':runtime, 'status':status, 'var':variables, 'obj':objective,
                  'assignment':assignment, 'gap':mipGap}        
        
        
    except gp.GurobiError as e:
        print('Error code ' + str(e.errno) + ': ' + str(e))
    
    except AttributeError:
        print('Encountered an attribute error')
        
    return output