import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { Activity, Trophy, Crosshair, MapPin } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

const COLORS = ['#8a2be2', '#ff006e', '#3a86ff', '#06d6a0', '#ffd166', '#ef476f', '#118ab2', '#073b4c'];

function App() {
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ seasons: [], teams: [] });
  const [selectedSeason, setSelectedSeason] = useState('');
  
  const [winRates, setWinRates] = useState([]);
  const [topBatsmen, setTopBatsmen] = useState([]);
  const [topBowlers, setTopBowlers] = useState([]);
  const [tossImpact, setTossImpact] = useState([]);
  const [venueTrends, setVenueTrends] = useState([]);

  useEffect(() => {
    fetchFilters();
  }, []);

  useEffect(() => {
    fetchAllStats();
  }, [selectedSeason]);

  const fetchFilters = async () => {
    try {
      const res = await axios.get(`${API_BASE}/filters`);
      setFilters(res.data);
    } catch (error) {
      console.error('Failed to fetch filters', error);
    }
  };

  const fetchAllStats = async () => {
    setLoading(true);
    const params = selectedSeason ? { season: selectedSeason } : {};
    try {
      const [winsRes, batRes, bowlRes, tossRes, venueRes] = await Promise.all([
        axios.get(`${API_BASE}/stats/win_rates`, { params }),
        axios.get(`${API_BASE}/stats/top_batsmen`, { params }),
        axios.get(`${API_BASE}/stats/top_bowlers`, { params }),
        axios.get(`${API_BASE}/stats/toss_impact`, { params }),
        axios.get(`${API_BASE}/stats/venue_trends`, { params })
      ]);
      
      setWinRates(winsRes.data);
      setTopBatsmen(batRes.data);
      setTopBowlers(bowlRes.data);
      setTossImpact(tossRes.data);
      setVenueTrends(venueRes.data);
    } catch (error) {
      console.error('Failed to fetch stats', error);
    } finally {
      setLoading(false);
    }
  };

  // Process Toss Data
  const tossData = [
    { name: 'Won Toss & Won Match', value: tossImpact.reduce((acc, curr) => acc + curr.matches_won_toss_won, 0) },
    { name: 'Lost Toss & Won Match', value: tossImpact.reduce((acc, curr) => acc + (curr.total_matches - curr.matches_won_toss_won), 0) }
  ];

  if (loading && !winRates.length) {
    return (
      <div className="loader-container">
        <div className="loader"></div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="header fade-in">
        <div className="title-container">
          <h1 className="gradient-text">IPL Analytics Engine</h1>
          <p>Real-time insights and strategic intelligence</p>
        </div>
        <div className="filter-bar">
          <select 
            value={selectedSeason} 
            onChange={(e) => setSelectedSeason(e.target.value)}
          >
            <option value="">All Seasons</option>
            {filters.seasons.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </header>

      <main className="dashboard-grid">
        {/* Win Rates Chart */}
        <div className="glass-panel col-span-8 fade-in" style={{ animationDelay: '0.1s' }}>
          <h3><Trophy size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--primary)' }}/> Win Rates by Team</h3>
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer>
              <BarChart data={winRates} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="team" stroke="var(--text-muted)" angle={-45} textAnchor="end" tick={{fontSize: 12}} interval={0} />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--surface-border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--text)' }}
                />
                <Bar dataKey="win_rate" name="Win Rate (%)" fill="var(--secondary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Toss Impact */}
        <div className="glass-panel col-span-4 fade-in" style={{ animationDelay: '0.2s' }}>
          <h3><Activity size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--success)' }}/> Toss Impact</h3>
          <div style={{ width: '100%', height: 350, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <ResponsiveContainer width="100%" height="80%">
              <PieChart>
                <Pie
                  data={tossData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {tossData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--surface-border)', borderRadius: '8px' }} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Batsmen Table */}
        <div className="glass-panel col-span-6 fade-in" style={{ animationDelay: '0.3s' }}>
          <h3><Crosshair size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--warning)' }}/> Top Batsmen</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>Runs</th>
                  <th>Strike Rate</th>
                </tr>
              </thead>
              <tbody>
                {topBatsmen.map((player, idx) => (
                  <tr key={idx}>
                    <td><span className="rank-badge">{idx + 1}</span></td>
                    <td style={{ fontWeight: 500 }}>{player.batter}</td>
                    <td style={{ color: 'var(--secondary)', fontWeight: 600 }}>{player.total_runs}</td>
                    <td>{player.strike_rate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Bowlers Table */}
        <div className="glass-panel col-span-6 fade-in" style={{ animationDelay: '0.4s' }}>
          <h3><Crosshair size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--primary-light)' }}/> Top Bowlers</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>Wickets</th>
                  <th>Economy</th>
                </tr>
              </thead>
              <tbody>
                {topBowlers.map((player, idx) => (
                  <tr key={idx}>
                    <td><span className="rank-badge">{idx + 1}</span></td>
                    <td style={{ fontWeight: 500 }}>{player.bowler}</td>
                    <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{player.wickets}</td>
                    <td>{player.economy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Venue Trends */}
        <div className="glass-panel col-span-12 fade-in" style={{ animationDelay: '0.5s' }}>
          <h3><MapPin size={20} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--danger)' }}/> Venue-wise Win Trends (Bat 1st vs Field 1st)</h3>
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer>
              <BarChart data={venueTrends} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="venue" stroke="var(--text-muted)" angle={-45} textAnchor="end" tick={{fontSize: 11}} interval={0} height={80} />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--surface-border)', borderRadius: '8px' }}
                />
                <Legend verticalAlign="top" height={36} />
                <Bar dataKey="bat_first_wins" name="Wins (Batting First)" fill="var(--primary)" radius={[4, 4, 0, 0]} stackId="a" />
                <Bar dataKey="field_first_wins" name="Wins (Fielding First)" fill="var(--secondary)" radius={[4, 4, 0, 0]} stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
