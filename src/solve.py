from ortools.sat.python import cp_model
import pandas as pd
from datetime import datetime

def get_data(commander_damage_filepath, boss_health_filepath):
    # Read commander damage output estimates
    commander_damage = pd.read_csv(commander_damage_filepath, index_col=[0,1])
    # Read csv with boss health data at each level
    # Could also require this to be a multi-index csv like the commander damage data
    bosses = pd.read_csv(boss_health_filepath)
    boss_names = bosses.columns[1:].tolist()
    # sort by level
    bosses = bosses.sort_values(by=['Level'])

    # Get the health of each boss for the given levels
    # convert string in 'XM' format to X*1e6 or 'XB' to X*1e9 for each entry in the dataframe
    for _, row in bosses.iterrows():
        # skip the first column which is the level
        for i in range(1, len(row)):
            health = row[i]
            if 'B' in health:
                bosses.at[_, row.index[i]] = int(float(health.split('B')[0]) * 1e9)
            elif 'M' in health:
                bosses.at[_, row.index[i]] = int(float(health.split('M')[0]) * 1e6)
            else:
                try:
                    bosses.at[_, row.index[i]] = int(health)
                except:
                    print(f'Could not parse health {health} for boss {row.index[i]} at level {row[0]}')
                    bosses.at[_, row.index[i]] = 0

    # Remove rows where all bosses have zero health
    bosses = bosses[(bosses.iloc[:,1:] != 0).any(axis=1)]

    # Get number of bosses that had zero health in the input csv
    # So we can remove them from the final count at the end
    N_bosses_with_zero_health = (bosses.iloc[:,1:] == 0).sum().sum()
    
    data = {}
    data['boss_health'] = bosses
    data['commander_damage'] = commander_damage

    data['all_commanders'] = range(len(commander_damage.columns))
    data['all_bosses'] = range(len(data['boss_health'].columns) - 1)
    data['N_bosses_with_zero_health'] = N_bosses_with_zero_health
    data['level_offset'] = bosses['Level'].iloc[0]
    # only need to check the first row b/c we removed rows with all zero health
    # get the index b/c that's how the loops are set up
    data['first_boss_without_zero_health'] = bosses.iloc[0,1:].to_numpy().nonzero()[0][0]

    return data, boss_names

def SearchForSolution(commander_damage_filepath, boss_health_filepath, attempts_per_commander, time_limit):
    # Creates the model
    model = cp_model.CpModel()

    # Get the commander and boss data
    data, boss_names = get_data(commander_damage_filepath, boss_health_filepath)
    N_bosses = len(boss_names)
    N_levels = len(data['boss_health'])
    
    # Define the variable if the commander is used for a boss
    # x[i, b, l] = n if commander i is used to damage boss b at level l, n times
    x = {}
    for i in data['all_commanders']:
        for b in data['all_bosses']:
            for l in range(N_levels):
                # # skip bosses with zero health
                # if data['boss_health'].iloc[l, b] > 0:
                x[i, b, l] = model.NewIntVar(0, attempts_per_commander, f'x_{i}_{b}_{l}')

    # Define the variable tracking if a boss is killed at each level
    # y[b, l] = 1 if boss b is killed at level l
    y = {}
    for b in data['all_bosses']:
        for l in range(N_levels):
            # # skip bosses with zero health
            # if b < data['first_boss_without_zero_health'] and l == 0:
            #     continue
            y[b, l] = model.NewBoolVar(f'y_{b}_{l}')

    # Define the variable tracking how much damage is done to a boss
    # z[b, l] = sum of damage done to boss b at level l
    max_boss_health = max(data['boss_health'].max())
    z = {}
    for b in data['all_bosses']:
        for l in range(N_levels):
            # # skip bosses with zero health
            # if b < data['first_boss_without_zero_health'] and l == 0:
            #     continue
            # Don't expect a boss to take more than twice its max health with overkill
            z[b, l] = model.NewIntVar(0, max_boss_health*2, f'z_{b}_{l}')

    " Create the constraints "
    # Each commander can only be used N times regardless of level
    for i in data['all_commanders']:
        # skip bosses with zero health
        model.Add(sum(x[i, b, l] for b in data['all_bosses'] for l in range(N_levels)) == attempts_per_commander)

    # Battle loop
    # Damage done to a boss is the sum of damage done by each commander
    # https://developers.google.com/optimization/cp/channeling
    # have to construct dummy boolean variables to use OnlyEnforceIf if we have multiple conditions
    # https://stackoverflow.com/a/38901246
    for b in data['all_bosses']:
        for l in range(N_levels):
            # skip bosses with zero health
            if b < data['first_boss_without_zero_health'] and l == 0:
                model.Add(z[b, l] == 0)
                model.Add(y[b, l] == 1)
                # force the commander usage to be zero since the boss has zero health
                for i in data['all_commanders']:
                    model.Add(x[i, b, l] == 0)
            else:
                # force the commander usage to be zero if the previous boss was not defeated
                for i in data['all_commanders']:
                    if b == data['first_boss_without_zero_health'] and l == 0:
                        # No restrictions for the first boss at the first level
                        continue
                    elif b == 0 and l > 0:
                        # The first boss can only be fought if last boss at the previous level was defeated
                        model.Add(x[i, b, l] == 0).OnlyEnforceIf(y[N_bosses-1, l-1].Not())
                    else:
                        # Can only fight the next boss after the previous boss is killed
                        model.Add(x[i, b, l] == 0).OnlyEnforceIf(y[b-1, l].Not())

                # Set the damage done to the boss
                damage_done = sum(x[i, b, l] * data['commander_damage'].iloc[:,i][boss_names[b], l] for i in data['all_commanders'])
                model.Add(z[b, l] == damage_done)
                # check if the boss is defeated
                model.Add(z[b, l] >= data['boss_health'][boss_names[b]].iloc[l]).OnlyEnforceIf(y[b, l])
                model.Add(z[b, l] < data['boss_health'][boss_names[b]].iloc[l]).OnlyEnforceIf(y[b, l].Not())

    " Objective "
    # Count the number of bosses killed
    # Compute the percentage of damage done to the last undefeated boss
    # Add the two together and scale to the nearest integer because the solver can only use integers
    # Maximize the scaled sum
    # Maxmizing the amount of damage done, clipped by a defeated boss's health, takes too long to solve
    scaling = int(1e2)
    objective = model.NewIntVar(0, scaling * N_bosses * N_levels, 'objective')
    last_boss_damage_fraction = {}
    scaled_damage = {}
    for l in range(N_levels):
        for b in data['all_bosses']:
            scaled_damage[b, l] = model.NewIntVar(0, max_boss_health*2*scaling, f'scaled_damage_{b}_{l}')
            last_boss_damage_fraction[b, l] = model.NewIntVar(0, scaling, 'last_boss_damage_fraction[b, l]')

            if b < data['first_boss_without_zero_health'] and l == 0:
                # if the boss has zero health, set the damage to zero
                model.Add(scaled_damage[b, l] == 0)
                model.Add(last_boss_damage_fraction[b, l] == 0)
            else:
                # only use the damage for the objective if the boss is not defeated
                # since previous bosses need to be defeated to fight the next boss, we only need to check if this boss was defeated or not
                model.Add(scaled_damage[b, l] == z[b, l] * scaling).OnlyEnforceIf(y[b, l].Not())
                model.Add(scaled_damage[b, l] == 0).OnlyEnforceIf(y[b, l])
                model.AddDivisionEquality(last_boss_damage_fraction[b, l], scaled_damage[b, l], data['boss_health'][boss_names[b]].iloc[l])

            
    sum_last_boss_damage_fraction = model.NewIntVar(0, scaling, 'sum_last_boss_damage_fraction')
    # has only one non-zero entry, but have to do it this way to get the solver to work
    model.Add(sum_last_boss_damage_fraction == sum(last_boss_damage_fraction[b, l] for b in data['all_bosses'] for l in range(N_levels)))

    N_bosses_defeated_scaled = model.NewIntVar(0, scaling * N_bosses * N_levels, 'N_bosses_defeated_scaled')
    N_bosses_defeated = sum(y[b, l] for b in data['all_bosses'] for l in range(N_levels)) - data['N_bosses_with_zero_health']
    model.Add(N_bosses_defeated_scaled == N_bosses_defeated * scaling )

    model.Add(objective == N_bosses_defeated_scaled + sum_last_boss_damage_fraction)
    model.Maximize(objective)

    # Create a solver and solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        solution_type = 'Optimal' if status == cp_model.OPTIMAL else 'Feasible'

        total_bosses_defeated = solver.ObjectiveValue()/scaling
        print_log = ''
        # Export the solution as a dictionary
        solution = {}
        total_damage = 0
        potential_total_damage = 0
        for l in range(N_levels):
            print_log += '------------------------'
            print_log += '\n'
            print_log += f'Level {l + data["level_offset"]} :'
            print_log += '\n'
            print_log += '------------------------'
            print_log += '\n'
            for b in data['all_bosses']:
                boss = boss_names[b]
                print_log += '------------------------'
                print_log += '\n'
                if l == 0 and b < data['first_boss_without_zero_health']:
                    print_log += f'{boss} was already defeated'
                else:
                    print_log += f'{boss} with {data["boss_health"][boss][l]:,.0f} health :'
                print_log += '\n'
                boss_damage = 0
                for i in data['all_commanders']:
                    if solver.Value(x[i, b, l]) > 0:
                        commander_name = data["commander_damage"].columns[i]
                        N_hits = solver.Value(x[i, b, l])
                        solution[f'commander_{i}_{b}_{l}'] = {}
                        solution[f'commander_{i}_{b}_{l}']['damage'] = N_hits * data['commander_damage'].iloc[:,i][boss_names[b], l]
                        solution[f'commander_{i}_{b}_{l}']['boss'] = boss_names[b]
                        # redundant, but makes it easier to parse later on
                        # increment by 1 so that it is 1-indexed to match the game
                        solution[f'commander_{i}_{b}_{l}']['level'] = l + data['level_offset']
                        solution[f'commander_{i}_{b}_{l}']['commander'] = commander_name
                        solution[f'commander_{i}_{b}_{l}']['N_hits'] = N_hits

                        potential_total_damage += solution[f'commander_{i}_{b}_{l}']['damage']
                        boss_damage += solution[f'commander_{i}_{b}_{l}']['damage']
                        
                        print_log += f'Commander {commander_name} with {data["commander_damage"].iloc[:,i][boss_names[b], l]:,.0f} damage, {N_hits} times'
                        print_log += '\n'
                
                overkill_damage = boss_damage - data['boss_health'][boss][l]
                if overkill_damage > 0:
                    total_damage += data['boss_health'][boss][l]
                    print_log += f'Overkill damage : {overkill_damage:,.0f}'
                    print_log += '\n'
                elif overkill_damage < 0 and overkill_damage != -data['boss_health'][boss][l]:
                    total_damage += boss_damage
                    print_log += f'Leftover health : {-overkill_damage:,.0f}'
                    print_log += '\n'

        # Damage efficiency compares the total damage with and without overkill
        damage_efficiency = total_damage / potential_total_damage * 100

        return solution, solution_type, print_log, boss_names, total_bosses_defeated, total_damage, damage_efficiency
    else:
        return None
