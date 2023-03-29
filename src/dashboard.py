import streamlit as st
import plotly.express as px
from solve import SearchForSolution
import pandas as pd

# Create sidebar to select number of attempts
num_attempts = st.sidebar.number_input('Select the number of attempts per commander', min_value=1, max_value=10, value=3, step=1)

# Create sidebar to select the time limit in seconds for the solver
time_limit = st.sidebar.number_input('Select the time limit in seconds for the solver. Longer gives more optimal results.', min_value=1, max_value=3600, value=60, step=1)

# Create sidebar to select csv file of boss health data
st.sidebar.markdown('Reupload the files if they are changed after the initial upload')
st.sidebar.title('Boss Health Data')
st.sidebar.markdown('Upload the csv file containing the boss health data')
boss_data_uploaded_file = st.sidebar.file_uploader("Choose a file", key='bd', type="csv")
if boss_data_uploaded_file is not None:
    st.sidebar.markdown('Boss health data uploaded successfully')
else:
    st.sidebar.markdown('No boss health data uploaded')

# Create sidebar to select csv file of commander damage data
st.sidebar.title('Commander Damage Data')
st.sidebar.markdown('Upload the csv file containing the commander damage data')
commander_data_uploaded_file = st.sidebar.file_uploader("Choose a file", key='cd', type="csv")
if commander_data_uploaded_file is not None:
    st.sidebar.markdown('Commander damage data uploaded successfully')
else:
    st.sidebar.markdown('No commander damage data uploaded')

# Create a button to run the solver only if both files are uploaded
if boss_data_uploaded_file is not None and commander_data_uploaded_file is not None:
    if st.sidebar.button('Run Solver'):
        # Run the solver
        solution, solution_type, print_log, boss_names, total_bosses_defeated, total_damage, damage_efficiency = \
            SearchForSolution(commander_data_uploaded_file, boss_data_uploaded_file, num_attempts, time_limit)
        
        # Display boss order
        st.title('Boss Order')
        st.markdown('The allowable attack order is determined by the column ordering in the boss health data file : ')
        st.text(boss_names)

        # Display the solution
        st.title('Results')
        if solution is not None:
            st.markdown(f'CP-SAT found a(n) **{solution_type}** solution')

            # print high level solution metrics
            st.markdown(f'Total bosses defeated: {total_bosses_defeated}')
            st.markdown(f'Total damage done (not including overkill): {total_damage:,.0f}')
            st.markdown(f'Damage efficiency : {damage_efficiency:,.2f} %')

            df = pd.DataFrame.from_dict(solution, orient='index')
            # sort by level for the plotly graph
            df = df.sort_values(by=['level'])
            # rename boss column to include the order
            df['boss'] = df['boss'].apply(lambda x: f'{boss_names.index(x)+1}. {x}')

            # plot as a horizontal bar graph with plotly
            fig = px.bar(df, x='damage', y='boss', color='level', hover_data=["commander"], 
                        orientation='h', height=600, color_continuous_scale=px.colors.qualitative.Plotly)
            fig.update_layout(
                xaxis_title='Damage Done',
                yaxis_title='Boss',
                yaxis={'categoryorder':'category ascending'},
                showlegend=False
            )
            st.plotly_chart(fig)

            # print out battle order
            st.markdown('Battle Order')
            st.text(print_log)

            st.markdown('Tabular Results')
            st.write(df)

        else:
            st.markdown('The solver failed to find a solution')

