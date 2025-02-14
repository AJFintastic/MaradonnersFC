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
    "Viv", "Minal", "Deelan", "Rush B", "Rush N", "Joe"
]

# --------------------------------------------------------------------
#                 CREATE LOCAL CSV IF NEEDED
# --------------------------------------------------------------------
def initialize_csv():
    """Ensures we have the columns in the exact format you want."""
    if not os.path.exists(LOCAL_DATA_FILE):
        columns = [
            "Date", "Time", "Pitch", "Opposition", "Score",
            "Players", "Scorers", "Assists", "Missed"
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
        # Force Score to be read as string, to avoid date auto‐conversion
        return pd.read_csv(LOCAL_DATA_FILE, dtype={"Score": "string"}).fillna("")
    else:
        return pd.DataFrame()

def save_local_data(df):
    # Ensure Score is stored as text so Excel doesn’t interpret it as a date
    df["Score"] = df["Score"].astype(str)
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
        # print("✅ League standings scraped and saved successfully.")
        # print(standings_df.head())

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

        # print("✅ All match results scraped successfully!")

        # print("✅ Match results scraped and saved successfully.")
        # print(results_df.head())

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
    - Appearances, Goals, Assists, Missed (?), etc.
    - You can expand as needed.
    """
    # Initialize dict
    stats = {
        p: {"Appearances": 0, "Goals": 0, "Assists": 0}
        for p in SQUAD
    }

    for _, row in df.iterrows():
        # Players
        players = row["Players"].split(", ") if row["Players"] else []
        # Scorers
        scorers_list = row["Scorers"].split(", ") if row["Scorers"] else []
        # Assists
        assists_list = row["Assists"].split(", ") if row["Assists"] else []
        # Missed
        missed_list = row["Missed"].split(", ") if "Missed" in df.columns and row["Missed"] else []

        # Appearances
        for p in players:
            stats[p]["Appearances"] += 1

        # Goals
        for s in scorers_list:
            # e.g. "AJ (2)"
            name, val = s.rsplit(" (", 1)
            g = int(val.rstrip(")"))
            stats[name.strip()]["Goals"] += g

        # Assists
        for a in assists_list:
            # e.g. "Himza (1)"
            name, val = a.rsplit(" (", 1)
            as_ = int(val.rstrip(")"))
            stats[name.strip()]["Assists"] += as_

    # Convert to DF
    stats_df = pd.DataFrame.from_dict(stats, orient="index").reset_index()
    stats_df.rename(columns={"index": "Player"}, inplace=True)

    return stats_df

def parse_score(score_str):
    """
    For local data: if "4 - 3", return (4,3). Otherwise None.
    """
    try:
        home, away = score_str.split("-")
        return int(home.strip()), int(away.strip())
    except:
        return None, None

def compute_team_metrics(df):
    """
    Compute team performance metrics from match data.
    """
    total_games = df.shape[0]
    total_goals_scored = df["Score"].apply(lambda x: int(x.split('-')[0]) if '-' in x else 0).sum()
    total_goals_conceded = df["Score"].apply(lambda x: int(x.split('-')[1]) if '-' in x else 0).sum()
    
    total_points = sum([3 if int(x.split('-')[0]) > int(x.split('-')[1]) else 
                        (1 if int(x.split('-')[0]) == int(x.split('-')[1]) else 0) 
                        for x in df["Score"] if '-' in x])

    avg_goals_scored = total_goals_scored / total_games if total_games > 0 else 0
    avg_goals_conceded = total_goals_conceded / total_games if total_games > 0 else 0
    win_rate = sum([1 if int(x.split('-')[0]) > int(x.split('-')[1]) else 0 for x in df["Score"] if '-' in x]) / total_games if total_games > 0 else 0
    
    # Count clean sheets (matches where goals conceded = 0)
    clean_sheets = sum([1 for x in df["Score"] if '-' in x and int(x.split('-')[1]) == 0])

    return {
        "Total Games": total_games,
        "Total Goals Scored": total_goals_scored,
        "Total Goals Conceded": total_goals_conceded,
        "Total Points": total_points,
        "Avg Goals Scored": avg_goals_scored,
        "Avg Goals Conceded": avg_goals_conceded,
        "Win Rate": win_rate,
        "Clean Sheets": clean_sheets
    }

# --------------------------------------------------------------------
#                           STREAMLIT UI
# --------------------------------------------------------------------
st.title("Maradonners FC")
st.subheader("👟💨⚽💨🥅", )

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
    score = st.text_input("🏆 Final Score (Maradonners 🆚 Opposition) e.g., **4 - 3**", placeholder="Enter score format: 4 - 3")

    # Player selection
    st.subheader("Players (Max 8)")
    selected_players = st.multiselect("Select players", SQUAD, default=SQUAD[:8], max_selections=8)

    # Missed Players
    missed_players = list(set(SQUAD) - set(selected_players))

    st.subheader("📊 Player Contributions")

    # Headings for Player Contributions Table
    cols = st.columns(6)
    with cols[0]:
        st.markdown("**Player**")
    with cols[1]:
        st.markdown("**Goals⚽**")
    with cols[2]:
        st.markdown("**Assists🎯**")
    with cols[3]:
        st.markdown("**Blue Card🟦**")
    with cols[4]:
        st.markdown("**Yellow Card🟨**")
    with cols[5]:
        st.markdown("**Red Card🟥**")

    # Dictionaries to store counts for each stat
    scorers_dict = {}
    assists_dict = {}
    blue_cards_dict = {}
    yellow_cards_dict = {}
    red_cards_dict = {}

    for player in selected_players:
        cols = st.columns(6)

        with cols[0]:
            st.markdown(f"**{player}**")

        with cols[1]:
            scorers_dict[player] = st.number_input(f"{player}_Goals", min_value=0, value=0, label_visibility="collapsed")

        with cols[2]:
            assists_dict[player] = st.number_input(f"{player}_Assists", min_value=0, value=0, label_visibility="collapsed")

        with cols[3]:
            blue_cards_dict[player] = st.number_input(f"{player}_Blue", min_value=0, value=0, label_visibility="collapsed")

        with cols[4]:
            yellow_cards_dict[player] = st.number_input(f"{player}_Yellow", min_value=0, value=0, label_visibility="collapsed")

        with cols[5]:
            red_cards_dict[player] = st.number_input(f"{player}_Red", min_value=0, value=0, label_visibility="collapsed")

    # Helper function to convert dictionary data to formatted string
    def dict_to_str(stat_dict):
        return ", ".join([f"{p} ({stat_dict[p]})" for p in stat_dict if stat_dict[p] > 0])

    if st.button("📌 Save Match Result"):
        new_row = {
            "Date": match_date.strftime("%d/%m/%Y"),
            "Time": match_time.strftime("%H:%M"),
            "Pitch": pitch,
            "Opposition": opposition,
            "Score": score,
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

        top_scorers = ", ".join(ps_df.loc[ps_df["Goals"] == top_goal_count, "Player"].tolist()) if top_goal_count > 0 else "N/A"
        most_appearances = ", ".join(ps_df.loc[ps_df["Appearances"] == most_apps_count, "Player"].tolist()) if most_apps_count > 0 else "N/A"

        # ========= STYLED TEAM METRICS =========
        st.subheader("⚽ Team Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Total Games Played", tm.get("Total Games", 0))
        with col2:
            st.metric("⚽ Total Goals Scored", tm.get("Total Goals Scored", 0))
        with col3:
            st.metric("🛑 Total Goals Conceded", tm.get("Total Goals Conceded", 0))
        with col4:
            st.metric("🏆 Total Points Earned", tm.get("Total Points", 0))

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("🔥 Avg Goals Scored/Game", round(tm.get("Avg Goals Scored", 0), 2))
        with col6:
            st.metric("🛡️ Avg Goals Conceded/Game", round(tm.get("Avg Goals Conceded", 0), 2))
        with col7:
            st.metric("🏅 Win Rate (%)", f"{round(tm.get('Win Rate', 0) * 100, 2)}%")
        with col8:
            st.metric("🧤 Clean Sheets", tm.get("Clean Sheets", 0))

        col9, col10 = st.columns(2)
        with col9:
            st.metric("⚡ Top Scorer(s)", top_scorers)
        with col10:
            st.metric("🎖️ Most Appearances", most_appearances)

        # ========= PLAYER STATS =========
        st.subheader("🏅 Player Statistics")

        # Ensure all squad members appear in the table, even if they haven't played
        squad_players = {player: {"Goals": 0, "Assists": 0, "Appearances": 0, "Missed Games": 0, 
                                "Yellow Cards": 0, "Red Cards": 0, "Blue Cards": 0} for player in SQUAD}

        # Fill stats from dataframe
        for _, row in ps_df.iterrows():
            player = row["Player"]
            squad_players[player] = {
                "Goals": row["Goals"],
                "Assists": row["Assists"],
                "Appearances": row["Appearances"],
                "Missed Games": row.get("Missed Games", 0),
                "Yellow Cards": row.get("Yellow Cards", 0),
                "Red Cards": row.get("Red Cards", 0),
                "Blue Cards": row.get("Blue Cards", 0),
            }

        # Convert to DataFrame
        ps_df_full = pd.DataFrame.from_dict(squad_players, orient="index").reset_index()
        ps_df_full.rename(columns={"index": "Player"}, inplace=True)

        # Sorting by Goals first, then Alphabetically
        ps_df_full = ps_df_full.sort_values(by=["Goals", "Player"], ascending=[False, True])

        st.dataframe(ps_df_full, height=458, hide_index=True)


        # ========= MATCH HISTORY =========
        st.subheader("📜 Match History")
        st.dataframe(df_local.drop(['Assists'], axis=1), hide_index=True)


# ================= TAB 3: LEAGUE (SCRAPED) ==================== #
with tab3:
    st.header("🏆 League Standings & Results")

    if st.button("Get latest League Data"):
        with st.spinner("Getting the latest league data..."):
            standings_df, results_df = scrape_league_data()
        st.success("League data updated!")

    st.subheader("League Standings")
    league_standings = load_league_standings()
    league_standings.index = league_standings.index + 1  # Start index from 1
    league_standings.drop(columns=["FF", "FA", "B"], inplace=True, errors="ignore")

    # 🔥 Add Fire Emoji for Maradonners
    league_standings["Team"] = league_standings["Team"].apply(
        lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
    )

    # 🔼 Add Up Arrow for Top 2 Teams
    if len(league_standings) >= 2:
        league_standings.loc[:2, "Team"] += " ⬆️"

    # 🔽 Add Down Arrow for Bottom 2 Teams
    if len(league_standings) >= 2:
        league_standings.loc[9:, "Team"] += " ⬇️"

    # Display the table
    if not league_standings.empty:
        st.dataframe(league_standings, use_container_width=True)
    else:
        st.info("No league standings data. Click 'Scrape League Data' above.")

    # ====================== LEAGUE MATCH RESULTS ====================== #
    st.subheader("League Match Results")
    league_results = load_league_results()
    league_results.index = league_results.index + 1  # Start index from 1

    # 🔥 Add Fire Emoji for Maradonners in Match Results
    league_results["Home Team"] = league_results["Home Team"].apply(
        lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
    )
    league_results["Away Team"] = league_results["Away Team"].apply(
        lambda x: f"🔥{x}🔥" if "Maradonners" in x else x
    )

    if not league_results.empty:
        st.dataframe(league_results, use_container_width=True)
    else:
        st.info("No league match results. Click 'Scrape League Data' above.")
