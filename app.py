import streamlit as st
import pandas as pd
import os
from datetime import datetime, time
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# --------------------------------------------------------------------
#                         FILE CONFIG
# --------------------------------------------------------------------
LOCAL_DATA_FILE = "maradonners_fc_results.csv"
LEAGUE_STANDINGS_FILE = "league_standings.csv"
LEAGUE_MATCH_RESULTS_FILE = "match_results.csv"

# Squad
SQUAD = [
    "AJ", "Himza", "Bir", "Bhavs", "Speirs", "Jakes",
    "Viv", "Minal", "Deelan", "Rush B", "Rush N", "Joe",
    "Filler"
]

# --------------------------------------------------------------------
#                 CREATE LOCAL CSV IF NEEDED
# --------------------------------------------------------------------
def initialize_csv():
    """Ensures we have the columns in the exact format you want."""
    if not os.path.exists(LOCAL_DATA_FILE):
        columns = [
            "Date", "Time", "Pitch", "Opposition",
            "Goals Scored", "Goals Conceded", "Own Goals",
            "Players", "Scorers", "Assists",
            "Blue Cards", "Yellow Cards", "Red Cards",
            "Missed"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_csv(LOCAL_DATA_FILE, index=False)

initialize_csv()

# --------------------------------------------------------------------
#                      SIMPLE LOGIN SYSTEM
# --------------------------------------------------------------------
st.sidebar.header("🔑 Login")

# User Credentials
USER_CREDENTIALS = {
    "Manager": "Manager@123",
    "Player": "Player@123"
}

# 🔹 Initialize session state if missing
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

# 🔹 If user is not authenticated, show login form
if not st.session_state["authenticated"]:
    user_role = st.sidebar.selectbox("Select Role", ["Manager", "Player"])
    password = st.sidebar.text_input("Enter Password", type="password")

    if st.sidebar.button("Login"):
        if USER_CREDENTIALS.get(user_role) == password:
            st.session_state["authenticated"] = True
            st.session_state["user_role"] = user_role
            st.sidebar.success(f"✅ Logged in as {user_role}")
            st.rerun()  # Refresh the app after login
        else:
            st.sidebar.error("❌ Incorrect Password")

    # 🔴 Stop the app if user is not logged in
    st.warning("🔐 Please log in to access the app.")
    st.stop()

# 🔹 Show welcome message & logout button
st.sidebar.info(f"🎉 Welcome, {st.session_state['user_role']}! You have full access.")

# 🔴 Logout Button (Clears Session & Forces Re-login)
if st.sidebar.button("🚪 Logout"):
    st.session_state["authenticated"] = False
    st.session_state["user_role"] = None
    st.rerun()  # Refresh app to enforce logout

# --------------------------------------------------------------------
#               LOADING AND SAVING LOCAL MATCH DATA
# --------------------------------------------------------------------
def load_local_data():
    if os.path.exists(LOCAL_DATA_FILE):
        # Important: the CSV now has 'Goals Scored', 'Goals Conceded', 'Own Goals'
        return pd.read_csv(
            LOCAL_DATA_FILE,
            dtype={"Goals Scored": "Int64", "Goals Conceded": "Int64", "Own Goals": "object"}  # Own Goals are stored as strings (player (1))
        ).fillna("")
    return pd.DataFrame(columns=[
        "Date", "Time", "Pitch", "Opposition", "Goals Scored", "Goals Conceded", "Own Goals",
        "Players", "Scorers", "Assists", "Blue Cards", "Yellow Cards", "Red Cards", "Missed"
    ])

def save_local_data(df):
    """Save the local data to CSV, preserving column order."""
    df.to_csv(LOCAL_DATA_FILE, index=False)

# --------------------------------------------------------------------
#           EXACT SCRAPING CODE (YOUR VERSION)
# --------------------------------------------------------------------
def scrape_league_data():
    """
    Scrapes league standings & results from the given URL,
    saving to league_standings.csv & match_results.csv.
    """
    url = (
        "https://discoverysoccerpark.spawtz.com/Leagues/Standings"
        "?SportId=0&VenueId=2&LeagueId=34&SeasonId=842&DivisionId=3430"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/132.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # ---- League Standings ----
    standings_table = soup.find("table", class_="STTable")
    standings_data = []
    standings_df = pd.DataFrame()  # fallback if no table found

    if standings_table:
        # Exclude the first column
        headers_row = [th.text.strip() for th in standings_table.find_all("td")[1:13]]
        for row in standings_table.find_all("tr")[1:]:
            cols = row.find_all("td")[1:13]
            if cols:
                standings_data.append([col.text.strip() for col in cols])

        standings_df = pd.DataFrame(standings_data, columns=headers_row)

        # Extract just the numeric part from "Pts"
        if "Pts" in standings_df.columns:
            standings_df["Pts"] = (
                standings_df["Pts"].str.extract(r"(\d+)").astype(int)
            )

        standings_df.to_csv(LEAGUE_STANDINGS_FILE, index=False)

    # ---- Match Results ----
    results_tables = soup.find_all("table", class_="FTable")  # Find ALL tables
    results_data = []

    if results_tables:
        for table in results_tables:  # Iterate through all tables
            rows = table.find_all("tr")
            match_date = ""

            for row in rows:
                if "FHeader" in row.get("class", []):
                    match_date = row.text.strip()  # Store match date
                cols = row.find_all("td")
                if len(cols) == 5:
                    # Extract match details: Date, Time, Pitch, Home Team, Score, Away Team
                    match_info = [match_date] + [col.text.strip() for col in cols]
                    results_data.append(match_info)

        # Convert to DataFrame
        results_headers = ["Date", "Time", "Pitch", "Home Team", "Score", "Away Team"]
        results_df = pd.DataFrame(results_data, columns=results_headers)

        # Remove "LIVE" from score text
        results_df["Score"] = results_df["Score"].str.replace("LIVE", "").str.strip()

        # Save to CSV
        results_df.to_csv(LEAGUE_MATCH_RESULTS_FILE, index=False)

    return standings_df, results_df

def load_league_standings():
    if os.path.exists(LEAGUE_STANDINGS_FILE):
        return pd.read_csv(LEAGUE_STANDINGS_FILE)
    return pd.DataFrame()

def load_league_results():
    if os.path.exists(LEAGUE_MATCH_RESULTS_FILE):
        return pd.read_csv(LEAGUE_MATCH_RESULTS_FILE)
    return pd.DataFrame()

# --------------------------------------------------------------------
#                        STATS FUNCTIONS
# --------------------------------------------------------------------
def compute_local_stats(df):
    """
    Build stats from local data:
    - Appearances, Goals, Assists, Missed Games, Own Goals, Blue Cards, Yellow Cards, Red Cards
    """
    stats = {
        p: {
            "Appearances": 0,
            "Goals": 0,
            "Own Goals": 0,
            "Assists": 0,
            "Missed Games": 0,
            "Blue Cards": 0,
            "Yellow Cards": 0,
            "Red Cards": 0
        }
        for p in SQUAD
    }

    for _, row in df.iterrows():
        # Players who played
        players = row["Players"].split(", ") if row["Players"] else []
        # Players who missed
        missed_list = row["Missed"].split(", ") if "Missed" in df.columns and row["Missed"] else []
        # Scorers
        scorers_list = row["Scorers"].split(", ") if row["Scorers"] else []
        # Own Goals
        own_goals_list = row["Own Goals"].split(", ") if row["Own Goals"] else []
        # Assists
        assists_list = row["Assists"].split(", ") if row["Assists"] else []
        
        # Cards
        blue_cards_list = row["Blue Cards"].split(", ") if row["Blue Cards"] else []
        yellow_cards_list = row["Yellow Cards"].split(", ") if row["Yellow Cards"] else []
        red_cards_list = row["Red Cards"].split(", ") if row["Red Cards"] else []

        # Count Appearances & Missed Games
        for p in players:
            stats[p]["Appearances"] += 1
        for p in missed_list:
            stats[p]["Missed Games"] += 1

        # Count Goals
        for s in scorers_list:
            try:
                name, val = s.rsplit(" (", 1)
                stats[name.strip()]["Goals"] += int(val.rstrip(")"))
            except:
                pass

        # Count Own Goals
        for og in own_goals_list:
            try:
                name, val = og.rsplit(" (", 1)
                stats[name.strip()]["Own Goals"] += int(val.rstrip(")"))
            except:
                pass

        # Count Assists
        for a in assists_list:
            try:
                name, val = a.rsplit(" (", 1)
                stats[name.strip()]["Assists"] += int(val.rstrip(")"))
            except:
                pass

        # Count Cards
        for bc in blue_cards_list:
            try:
                name, val = bc.rsplit(" (", 1)
                stats[name.strip()]["Blue Cards"] += int(val.rstrip(")"))
            except:
                pass

        for yc in yellow_cards_list:
            try:
                name, val = yc.rsplit(" (", 1)
                stats[name.strip()]["Yellow Cards"] += int(val.rstrip(")"))
            except:
                pass

        for rc in red_cards_list:
            try:
                name, val = rc.rsplit(" (", 1)
                stats[name.strip()]["Red Cards"] += int(val.rstrip(")"))
            except:
                pass

    # Convert to DataFrame
    stats_df = pd.DataFrame.from_dict(stats, orient="index").reset_index()
    stats_df.rename(columns={"index": "Player"}, inplace=True)

    return stats_df



def compute_team_metrics(df):
    """
    Compute team performance metrics from match data.
    """
    if df.empty:
        return {
            "Total Games": 0,
            "Total Goals Scored": 0,
            "Total Goals Conceded": 0,
            "Total Points": 0,
            "Avg Goals Scored": 0,
            "Avg Goals Conceded": 0,
            "Win Rate": 0,
            "Clean Sheets": 0
        }

    # Extract data safely
    total_games = df.shape[0]
    # Convert columns to numeric if needed
    df["Goals Scored"] = pd.to_numeric(df["Goals Scored"], errors="coerce").fillna(0)
    df["Goals Conceded"] = pd.to_numeric(df["Goals Conceded"], errors="coerce").fillna(0)

    total_goals_scored = df["Goals Scored"].sum()
    total_goals_conceded = df["Goals Conceded"].sum()

    # Calculate points
    total_points = sum(
        3 if row["Goals Scored"] > row["Goals Conceded"] else
        1 if row["Goals Scored"] == row["Goals Conceded"] else 0
        for _, row in df.iterrows()
    )

    # Averages & Win Rate
    avg_goals_scored = total_goals_scored / total_games if total_games > 0 else 0
    avg_goals_conceded = total_goals_conceded / total_games if total_games > 0 else 0
    win_rate = (
        sum(1 for _, row in df.iterrows() if row["Goals Scored"] > row["Goals Conceded"])
        / total_games
        if total_games > 0
        else 0
    )

    # Count clean sheets (Games where Goals Conceded = 0)
    clean_sheets = sum(1 for _, row in df.iterrows() if row["Goals Conceded"] == 0)

    return {
        "Total Games": int(total_games),
        "Total Goals Scored": int(total_goals_scored),
        "Total Goals Conceded": int(total_goals_conceded),
        "Total Points": int(total_points),
        "Avg Goals Scored": round(avg_goals_scored, 2),
        "Avg Goals Conceded": round(avg_goals_conceded, 2),
        "Win Rate": round(win_rate * 100, 2),  # Convert to %
        "Clean Sheets": clean_sheets
    }

# --------------------------------------------------------------------
#                           STREAMLIT UI
# --------------------------------------------------------------------
st.title("Maradonners FC")
st.subheader("👟💨⚽💨🥅")

tab1, tab2, tab3 = st.tabs(["📋 Enter Match Results", "📊 Stats & Metrics", "🏆 League"])

# ================= TAB 1: ENTER MATCH RESULTS ==================== #
with tab1:
    st.header("📋 Enter Match Results")

    colA, colB, colC = st.columns(3)
    with colA:
        match_date = st.date_input("Match Date", value=datetime.today())
    with colB:
        match_time = st.time_input("Match Time", value=time(21, 0))
    with colC:
        pitch = st.text_input("Pitch", "Pitch 4")

    opposition = st.text_input("Opposition", "")
    score_input = st.text_input("🏆 Final Score (Maradonners 🆚 Opposition) e.g., 4 - 3",
                                placeholder="Enter score format: 4 - 3")

    st.markdown("---")
        
    # Player selection
    st.subheader("Players (Max 8)")
    selected_players = st.multiselect(
        "Select players", SQUAD, default=SQUAD[:8], max_selections=8
    )

    # Missed Players
    missed_players = list(set(SQUAD) - set(selected_players))

    st.subheader("📊 Player Contributions")

    # Headings for Player Contributions Table
    cols_header = st.columns(7)
    with cols_header[0]:
        st.markdown("**Player**")
    with cols_header[1]:
        st.markdown("**Goals⚽**")
    with cols_header[2]:
        st.markdown("**Assists🎯**")
    with cols_header[3]:
        st.markdown("**Blue Card🟦**")
    with cols_header[4]:
        st.markdown("**Yellow Card🟨**")
    with cols_header[5]:
        st.markdown("**Red Card🟥**")
    with cols_header[6]:
        st.markdown("**Own Goals⚠️**")

    # Dictionaries to store counts for each stat
    scorers_dict = {}
    assists_dict = {}
    blue_cards_dict = {}
    yellow_cards_dict = {}
    red_cards_dict = {}
    own_goals_dict = {}

    for player in selected_players:
        row_cols = st.columns(7)
        with row_cols[0]:
            st.markdown(f"**{player}**")
        with row_cols[1]:
            scorers_dict[player] = st.number_input(
                f"{player}_Goals", min_value=0, value=0, label_visibility="collapsed"
            )
        with row_cols[2]:
            assists_dict[player] = st.number_input(
                f"{player}_Assists", min_value=0, value=0, label_visibility="collapsed"
            )
        with row_cols[3]:
            blue_cards_dict[player] = st.number_input(
                f"{player}_Blue", min_value=0, value=0, label_visibility="collapsed"
            )
        with row_cols[4]:
            yellow_cards_dict[player] = st.number_input(
                f"{player}_Yellow", min_value=0, value=0, label_visibility="collapsed"
            )
        with row_cols[5]:
            red_cards_dict[player] = st.number_input(
                f"{player}_Red", min_value=0, value=0, label_visibility="collapsed"
            )
        with row_cols[6]:
            own_goals_dict[player] = st.number_input(
                f"{player}_OwnGoals", min_value=0, value=0, step=1, label_visibility="collapsed"
            )

    # Helper function to convert dictionary data to a string "Name (X), Name2 (Y)"
    def dict_to_str(stat_dict):
        return ", ".join([f"{p} ({stat_dict[p]})" for p in stat_dict if stat_dict[p] > 0])

    if st.button("📌 Save Match Result"):
        # Try to parse the user-entered score
        try:
            # remove spaces around the dash if needed
            goals_scored, goals_conceded = map(int, score_input.replace(" ", "").split("-"))
        except ValueError:
            st.error("❌ Invalid score format. Please enter something like '4 - 3' (Maradonners first).")
            # Do NOT stop the entire app; just skip saving
        else:
            # Check total player goals vs. user-entered "Goals Scored"
            total_player_goals = sum(scorers_dict.values())
            total_own_goals = sum(own_goals_dict.values())

            # Adjust goals conceded to include own goals
            adjusted_goals_conceded = goals_conceded + total_own_goals

            if total_player_goals != goals_scored:
                st.error(
                    f"❌ Total goals scored ({goals_scored}) does not match Player Goals ({total_player_goals}). "
                    "Please correct the inputs."
                )
            else:
                # Construct new row
                new_row = {
                    "Date": match_date.strftime("%d/%m/%Y"),
                    "Time": match_time.strftime("%H:%M"),
                    "Pitch": pitch,
                    "Opposition": opposition,
                    "Goals Scored": goals_scored,
                    "Goals Conceded": adjusted_goals_conceded,  # Includes Own Goals
                    "Own Goals": dict_to_str(own_goals_dict),
                    "Players": ", ".join(selected_players),
                    "Scorers": dict_to_str(scorers_dict),
                    "Assists": dict_to_str(assists_dict),
                    "Blue Cards": dict_to_str(blue_cards_dict),
                    "Yellow Cards": dict_to_str(yellow_cards_dict),
                    "Red Cards": dict_to_str(red_cards_dict),
                    "Missed": ", ".join(missed_players),
                }

                df_local = load_local_data()
                df_local = pd.concat([df_local, pd.DataFrame([new_row])], ignore_index=True)
                save_local_data(df_local)
                st.success("✅ Match result saved successfully!")

# ================= TAB 2: STATS & METRICS ==================== #
# ================= TAB 2: STATS & METRICS ==================== #
with tab2:
    st.header("📊 Stats & Metrics")

    df_local = load_local_data()

    if df_local.empty:
        st.warning("⚠️ No data found. Please add match results first.")
    else:
        # ========= COMPUTE METRICS =========
        tm = compute_team_metrics(df_local)
        ps_df = compute_local_stats(df_local)

        # ========= FIND MULTIPLE TOP SCORERS & MOST APPEARANCES =========
        top_goal_count = ps_df["Goals"].max()
        most_apps_count = ps_df["Appearances"].max()

        if top_goal_count > 0:
            top_scorers = ", ".join(
                ps_df.loc[ps_df["Goals"] == top_goal_count, "Player"].tolist()
            )
        else:
            top_scorers = "N/A"

        if most_apps_count > 0:
            most_appearances = ", ".join(
                ps_df.loc[ps_df["Appearances"] == most_apps_count, "Player"].tolist()
            )
        else:
            most_appearances = "N/A"

        # ========= STYLED TEAM METRICS =========
        st.subheader("⚽ Team Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Total Games", tm["Total Games"])
        with col2:
            st.metric("⚽ Goals Scored", tm["Total Goals Scored"])
        with col3:
            st.metric("🛑 Goals Conceded", tm["Total Goals Conceded"])
        with col4:
            st.metric("🏆 Points Earned", tm["Total Points"])

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("🔥 Avg Scored/Game", tm["Avg Goals Scored"])
        with col6:
            st.metric("🛡️ Avg Conceded/Game", tm["Avg Goals Conceded"])
        with col7:
            st.metric("🏅 Win Rate (%)", tm["Win Rate"])
        with col8:
            st.metric("🧤 Clean Sheets", tm["Clean Sheets"])

        # Already calculated:
        #   top_scorers
        #   most_appearances
        
        st.markdown("---")

        col9, col10 = st.columns(2)
        with col9:
            st.metric("⚡ Top Scorer(s)", top_scorers)
        with col10:
            st.metric("🎖️ Most Appearances", most_appearances)

        # ====== NEW METRICS: Most Games Missed, Blue Cards, Yellow Cards, Own Goals ======
        max_missed_count = ps_df["Missed Games"].max()
        if max_missed_count > 0:
            most_missed_players = ", ".join(ps_df.loc[ps_df["Missed Games"] == max_missed_count, "Player"])
        else:
            most_missed_players = "N/A"

        max_blue_cards = ps_df["Blue Cards"].max()
        if max_blue_cards > 0:
            most_blue_cards_players = ", ".join(ps_df.loc[ps_df["Blue Cards"] == max_blue_cards, "Player"])
        else:
            most_blue_cards_players = "N/A"

        max_yellow_cards = ps_df["Yellow Cards"].max()
        if max_yellow_cards > 0:
            most_yellow_cards_players = ", ".join(ps_df.loc[ps_df["Yellow Cards"] == max_yellow_cards, "Player"])
        else:
            most_yellow_cards_players = "N/A"

        max_own_goals = ps_df["Own Goals"].max()
        if max_own_goals > 0:
            most_own_goals_players = ", ".join(ps_df.loc[ps_df["Own Goals"] == max_own_goals, "Player"])
        else:
            most_own_goals_players = "N/A"

        col11, col12 = st.columns(2)
        with col11:
            st.metric("🙈 Most Games Missed", most_missed_players)
        with col12:
            st.metric("🟦 Most Blue Cards", most_blue_cards_players)

        col13, col14 = st.columns(2)
        with col13:
            st.metric("🟨 Most Yellow Cards", most_yellow_cards_players)
        with col14:
            st.metric("⚠️ Most Own Goals", most_own_goals_players)

        st.markdown("---")
        
        # ============ PLAYER STATS (Detailed) ============
        st.subheader("🏅 Player Statistics")

        # Initialize a dictionary so *every* SQUAD member appears even if zero stats
        squad_stats = {
            p: {
                "Appearances": 0,
                "Missed Games": 0,
                "Goals": 0,
                "Own Goals": 0,
                "Assists": 0,
                "Blue Cards": 0,
                "Yellow Cards": 0,
                "Red Cards": 0
            }
            for p in SQUAD
        }

        # Merge stats from ps_df into squad_stats
        # ps_df columns now:
        # [Player, Appearances, Goals, Own Goals, Assists, Missed Games,
        #  Blue Cards, Yellow Cards, Red Cards]
        for idx, row in ps_df.iterrows():
            p = row["Player"]
            if p in squad_stats:
                squad_stats[p]["Appearances"] = row["Appearances"]
                squad_stats[p]["Missed Games"] = row["Missed Games"]
                squad_stats[p]["Goals"] = row["Goals"]
                squad_stats[p]["Own Goals"] = row["Own Goals"]
                squad_stats[p]["Assists"] = row["Assists"]
                squad_stats[p]["Blue Cards"] = row["Blue Cards"]
                squad_stats[p]["Yellow Cards"] = row["Yellow Cards"]
                squad_stats[p]["Red Cards"] = row["Red Cards"]

        # Build final DF
        ps_df_full = pd.DataFrame.from_dict(squad_stats, orient="index").reset_index()
        ps_df_full.rename(columns={"index": "Player"}, inplace=True)

        # Sort primarily by Goals (descending), then by Player name
        ps_df_full = ps_df_full.sort_values(by=["Goals", "Player"], ascending=[False, True])

        # Optionally reorder columns for neat display
        columns_order = [
            "Player", "Appearances", "Missed Games", "Goals",
            "Assists", "Blue Cards", "Yellow Cards", "Red Cards", "Own Goals"
        ]
        ps_df_full = ps_df_full[columns_order]

        # Reset index to ensure a clean append
        ps_df_full = ps_df_full.reset_index(drop=True)

        # Create a totals row
        totals_dict = {}
        for col in columns_order:
            if col == "Player":
                totals_dict[col] = "TOTAL"
            else:
                # Sum up numeric columns
                totals_dict[col] = ps_df_full[col].sum(numeric_only=True)

        # Append the totals row to the end
        ps_df_full = pd.concat([ps_df_full, pd.DataFrame([totals_dict])], ignore_index=True)

        # Display DataFrame with totals row
        st.dataframe(ps_df_full, use_container_width=True, hide_index=True, height=492)

        st.markdown("---")
        
        # ========= MATCH HISTORY =========
        st.subheader("📜 Match History")
        st.dataframe(df_local, use_container_width=True, hide_index=True, height=420)


# ================= TAB 3: LEAGUE (SCRAPED) ==================== #
with tab3:
    st.header("🏆 League Standings & Results")

    if st.button("Get latest League Data"):
        with st.spinner("Getting the latest league data..."):
            standings_df, results_df = scrape_league_data()
        st.success("League data updated!")

    st.subheader("League Standings")
    league_standings = load_league_standings()
    if not league_standings.empty:
        # Adjust index
        league_standings.index = league_standings.index + 1
        # Drop columns if they exist
        league_standings.drop(columns=["FF", "FA", "B"], inplace=True, errors="ignore")

        # 🔥 Mark Maradonners
        if "Team" in league_standings.columns:
            league_standings["Team"] = league_standings["Team"].apply(
                lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
            )
            # Mark top 2 up-arrow, bottom 2 down-arrow
            if len(league_standings) >= 2:
                league_standings.loc[1:2, "Team"] += " ⬆️"
                league_standings.loc[len(league_standings) - 1 : len(league_standings), "Team"] += " ⬇️"

        st.dataframe(league_standings, use_container_width=True)
    else:
        st.info("No league standings data. Click 'Get latest League Data' to scrape.")

    st.markdown("---")
        
    # ====================== LEAGUE MATCH RESULTS ====================== #
    st.subheader("League Match Results")
    league_results = load_league_results()

    if not league_results.empty:
        league_results.index = league_results.index + 1
        # 🔥 Highlight Maradonners
        if "Home Team" in league_results.columns:
            league_results["Home Team"] = league_results["Home Team"].apply(
                lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
            )
        if "Away Team" in league_results.columns:
            league_results["Away Team"] = league_results["Away Team"].apply(
                lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
            )
        st.dataframe(league_results, use_container_width=True)
    else:
        st.info("No match results data. Click 'Get latest League Data' to scrape.")
