import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { useAuth } from '../context/AuthContext';
import { useApi } from '../hooks/useApi';
import { PageHeader, Loading, ErrorState, Empty, Badge, formatDate } from '../components/ui';

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const axisTick = { fontSize: 12, fill: 'var(--muted)' };

export function PerformanceCharts({ data }) {
  const m = data.metrics;
  return <><div className="chart-grid">
    <section className="panel"><div className="panel-heading"><div><h2>Performance over time</h2><p>Average evaluated score</p></div></div>
      {data.trends.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.trends} margin={{ top:10, right:20, left:-25, bottom:0 }}><defs><linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.12}/><stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="var(--border)"/><XAxis dataKey="date" tick={axisTick} axisLine={false} tickLine={false}/><YAxis domain={[0,100]} tick={axisTick} axisLine={false} tickLine={false}/><Tooltip/><Area type="monotone" dataKey="score" name="Average score" stroke="var(--chart-1)" strokeWidth={2} fill="url(#scoreFill)" dot={{ r:3, fill:'var(--chart-1)' }}/></AreaChart></ResponsiveContainer></div>
        : <Empty title="No scores yet" description="The trend appears once results are evaluated and released."/>}</section>
    <section className="panel"><div className="panel-heading"><div><h2>Assignment completion</h2><p>Completed versus pending</p></div></div>
      {m.assigned_assignments ? <div className="completion-chart"><ResponsiveContainer width="100%" height={200}><PieChart><Pie data={[{name:'Completed',value:m.completed_assignments},{name:'Pending',value:m.pending_assignments}]} innerRadius={67} outerRadius={85} paddingAngle={0} dataKey="value" stroke="none"><Cell fill="var(--chart-1)"/><Cell fill="var(--border)"/></Pie><Tooltip/></PieChart></ResponsiveContainer><div className="donut-label"><strong>{m.completion_percentage}%</strong><span>completed</span></div><div className="completion-legend"><span><i style={{background:'var(--chart-1)'}}/>Completed <b>{m.completed_assignments}</b></span><span><i style={{background:'var(--border-strong)'}}/>Pending <b>{m.pending_assignments}</b></span></div></div>
        : <Empty title="Nothing assigned yet" description="Completion is tracked once an assignment is assigned."/>}</section></div>
    <div className="chart-grid equal">
      <section className="panel"><div className="panel-heading"><div><h2>Topic scores</h2><p>Average score per topic</p></div></div>
        {data.topic_scores.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.topic_scores} layout="vertical" margin={{left:10,right:25}}><XAxis type="number" domain={[0,100]} hide/><YAxis type="category" dataKey="name" width={110} tick={axisTick} axisLine={false} tickLine={false}/><Tooltip cursor={{fill:'var(--surface-subtle)'}}/><Bar dataKey="score" name="Score" fill="var(--chart-1)" radius={[0,3,3,0]} barSize={14}/></BarChart></ResponsiveContainer></div>
          : <Empty title="No topic scores yet" description="Topic averages use evaluated results only."/>}</section>
      <section className="panel"><div className="panel-heading"><div><h2>Score distribution</h2><p>Results in each score band</p></div></div>
        {data.distribution.some(x=>x.count) ? <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.distribution}><CartesianGrid vertical={false} stroke="var(--border)"/><XAxis dataKey="name" axisLine={false} tickLine={false} tick={axisTick}/><YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={axisTick}/><Tooltip cursor={{fill:'var(--surface-subtle)'}}/><Bar dataKey="count" name="Results" fill="var(--chart-2)" radius={[3,3,0,0]} barSize={36}/></BarChart></ResponsiveContainer></div>
          : <Empty title="No results yet" description="The distribution fills in as results are evaluated."/>}</section></div></>;
}

export default function Dashboard() {
  const { user } = useAuth(); const trainer = user.role !== 'student'; const manager = ['admin','sales'].includes(user.role);
  const { data, loading, error, reload } = useApi(trainer ? '/admin/dashboard/' : '/student/dashboard/');
  if (loading) return <Loading/>; if (error) return <ErrorState message={error} retry={reload}/>;
  const m = data.metrics;
  // A 0% average with nothing evaluated reads as failure; show a dash until there is evidence.
  const scored = data.distribution.some(x => x.count);
  const average = scored ? `${m.average_score}%` : '—';
  const stats = trainer
    ? [['Students', m.total_students, `${m.active_students} active`], ['Assignments', m.total_assignments, `${m.published_assignments} published`], ['Submissions', m.total_submissions, `${m.pending_evaluations} awaiting review`], ['Average score', average, scored ? 'Evaluated results' : 'Nothing evaluated yet']]
    : [['Assigned', m.assigned_assignments, `${m.pending_assignments} to complete`], ['Completed', m.completed_assignments, `${m.completion_percentage}% of assigned`], ['Average score', average, scored ? 'Released results' : 'No released results yet'], ['Overdue', m.overdue_assignments, m.overdue_assignments ? 'Past the deadline' : 'Nothing overdue']];
  const nextSteps = manager ? [
    { to:'/students', title:'Students', detail:'Approve emails and manage access.', label:'Manage students' },
    { to:'/batches', title:'Batches', detail:'Group a course, a trainer, and students.', label:'Manage batches' },
    { to:'/performance', title:'Performance', detail:'Find students who need support.', label:'View performance' },
  ] : trainer ? [
    { to:'/submissions?status=submitted', title: m.pending_evaluations ? `${plural(m.pending_evaluations,'submission')} to review` : 'Review queue is clear', detail:'Grade submitted work and leave feedback.', label:'Review submissions' },
    { to:'/assignments/new', title:'New assignment', detail:'Write questions, set a deadline, assign it.', label:'Create an assignment' },
    { to:'/batches', title:'Your batches', detail:'Rosters, assignments, and progress by group.', label:'Open batches' },
  ] : [
    { to:'/assignments', title: m.pending_assignments ? `${plural(m.pending_assignments,'assignment')} to complete` : 'All assignments done', detail:'Open your work and continue where you stopped.', label:'Open assignments' },
    { to:'/submissions', title:'Feedback', detail:'Your answers and released results.', label:'View submissions' },
    { to:'/learning-path', title:'Learning path', detail:'What to practise next, based on your results.', label:'View learning path' },
  ];
  return <>
    <PageHeader title={`Welcome back, ${user.name.split(' ')[0]}.`} description={manager ? 'Students, courses, batches, and results across the organisation.' : trainer ? 'Your batches, work waiting for review, and recent results.' : 'Your assignments, deadlines, and results.'}>
      <Link className="btn btn-secondary" to="/performance">Performance</Link>
      {trainer && <Link className="btn btn-primary" to={manager ? '/team' : '/batches'}>{manager ? 'Manage team' : 'My batches'}</Link>}
    </PageHeader>
    <div className="stats-grid">{stats.map(([label,value,note]) => <section className="stat-card" key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></section>)}</div>
    <section className="next-steps" aria-labelledby="next-steps-title"><div className="section-heading"><h2 id="next-steps-title">Next up</h2></div>
      <div className="next-step-grid">{nextSteps.map(({to,title,detail,label}) => <Link to={to} className="next-step-card" key={to}><h3>{title}</h3><p>{detail}</p><span className="next-step-link">{label}<ArrowRight size={15}/></span></Link>)}</div></section>
    <div className="chart-grid activity-grid">
      <section className="panel"><div className="panel-heading"><div><h2>Recent submissions</h2><p>{trainer ? 'Latest work across your batches' : 'Your latest attempts'}</p></div><Link to="/submissions" className="text-link">View all</Link></div>
        {data.recent_submissions.length ? <div className="table-wrap" tabIndex={0} role="region" aria-label="Recent submissions"><table><thead><tr><th scope="col">Assignment</th>{trainer && <th scope="col">Student</th>}<th scope="col">Status</th><th scope="col">Score</th></tr></thead><tbody>{data.recent_submissions.slice(0,5).map(s => <tr key={s.id}><td><Link to={`/submissions/${s.id}`}>{s.assignment}</Link><small>{formatDate(s.date)}</small></td>{trainer && <td>{s.student}</td>}<td><Badge>{s.status}</Badge></td><td>{s.percentage === null ? '—' : `${s.percentage}%`}</td></tr>)}</tbody></table></div>
          : <Empty title="No submissions yet" description="Submitted work appears here."/>}</section>
      <section className="panel"><div className="panel-heading"><div><h2>Upcoming deadlines</h2><p>Next five due</p></div></div>
        {data.upcoming.length ? <div className="deadline-list">{data.upcoming.slice(0,5).map(a => <Link to={`/assignments/${a.id}`} key={a.id}><div><strong>{a.title}</strong><small>{formatDate(a.deadline)}</small></div><ArrowRight size={16}/></Link>)}</div>
          : <Empty title="No upcoming deadlines"/>}</section></div>
    {m.coding_tests_total > 0 && <section className="output-summary"><div><span className="eyebrow">Output accuracy</span><h2>{m.coding_accuracy}% matched</h2><p>{m.coding_tests_passed} of {plural(m.coding_tests_total,'output check')} passed</p></div><div className="output-meter" role="meter" aria-label="Output accuracy" aria-valuenow={m.coding_accuracy} aria-valuemin={0} aria-valuemax={100}><span style={{width:`${m.coding_accuracy}%`}}/></div></section>}
    <PerformanceCharts data={data}/>
  </>;
}
