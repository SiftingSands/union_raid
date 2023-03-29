# Description

Attempts to find the optimal commander battle order for union raids. Originally made for the Pockult union.

Assumptions:
- The amount of damage dealt by each commander is known for each boss and at each level
    - No variance term is modeled in the damage dealt by each commander (i.e. not performing a Monte Carlo simulation and displaying the statistics)
- The amount of health per boss is known at every level
- Only one day of raids are being considered. A user would have to update the boss health for day N using the results from day N-1 and run the solver again.

# Background

- Uses the CP-SAT solver in the OR-Tools library (https://developers.google.com/optimization)
- Constraints:
  - Each commander can only be used N times (user set parameter in the dashboard), but a commander can be used more than once at a boss
  - A boss must be defeated before the next boss can be attacked
  - All bosses at a level must be defeated before the next level can be started
- Objective:
  - Maximize the number of bosses defeated and the amount of damage dealt to the last un-defeated boss
  * Maximizing the total damage dealt to all bosses seems to be a harder problem for the solver (numerics?)
  * Rounding all damage to the nearest 100K or 1M might help the solver but would require some refactoring
- CP-SAT will utilize all available CPU cores on the machine! Can wind up acting as a CPU stress test.

# Installation and Startup

## Run with Streamlit Cloud
1. Go to https://share.streamlit.io/ and paste in the URL of this repo
    -

## Run with Python
1. Install all Python dependencies
    - `pip install -r requirements.txt`
2. Run the dashboard
    - `streamlit run src/dashboard.py`
    - OR use a different port other than the default 8501
        - `streamlit run src/dashboard.py --server.port <port>`
3. Open up the dashboard in your browser if it doesn't open automatically
    - `http://localhost:<port>`

# Usage

1. Set the number of times each commander can be used
2. Set the time limit for the solver to run
3. Give the CSV with the damage dealt by each commander to each boss
4. Give the CSV with the health of each boss at each level
5. Click the "Run Solver" button
6. The solver will run for the specified time limit and display the results
Results include a interactive bar chart, a printout of the battle order, and a table of the solution output.

- Sample CSVs are provided in the `assets` folder so the user can see the expected data format
  - `python src/synthetic_commander_damage_data.py` will generate a sample CSV with random damage (using an upper to lower bound) dealt by each commander to each boss that is linearly decreasing from boss level 1 to 10 and from commander 1 to 32.

# Limitations

1. Estimating how much damage each commander deals to each boss likely has a high variance, and is possibly multi-modal given the game mechanics. This is the major limiting factor on the usability of the solver's output.
2. Solver may not find an optimal solution if the time limit is too short, or if the raid setup presents a very challenging problem. Dramatically increasing the time limit may not significantly increase the number of bosses defeated. A few minutes seems to be a good rule of thumb.

# Notes on making binaries
- Could not get a Windows installer (https://github.com/takluyver/pynsist) built using Pynsist to work. The installer would run, but the Streamlit dashboard would not load. Their example streamlit app worked fine, so it might be due to the later version of Streamlit used in this project or the use of OR-Tools.
- Pyinstaller does not work in a straightforward manner with Streamlit, so a portable executable was not built.
