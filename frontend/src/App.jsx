import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider, Loading, Empty } from './components/ui';
import AppLayout from './layouts/AppLayout';
import AuthPage from './pages/auth/AuthPages';
import Dashboard from './pages/Dashboard';
import { StudentsPage, CoursesPage } from './pages/admin/Management';
import { StaffPage, BatchesPage } from './pages/admin/TeamBatches';
import MaterialsPage from './pages/admin/Materials';
import GeneratorPage from './pages/admin/Generator';
import { AssignmentsPage, AssignmentDetail } from './pages/assignments/Assignments';
import AssignmentEditor from './pages/assignments/AssignmentEditor';
import Workspace from './pages/coding/Workspace';
import { SubmissionsPage, SubmissionDetail } from './pages/submissions/Submissions';
import { ReportsPage, ReportDetail, LearningPath } from './pages/reports/Reports';
import { PerformancePage, LeaderboardPage, NotificationsPage, SettingsPage, ProfilePage } from './pages/OtherPages';
import { APP_BASE_PATH } from './utils/paths';
function Protected({ role }) { const {user,loading}=useAuth();if(loading)return <div className="boot-loading"><Loading/></div>;if(!user)return <Navigate to="/login" replace/>;if(role&&!(Array.isArray(role)?role:[role]).includes(user.role))return <Navigate to="/" replace/>;return <Outlet/>; }
export default function App(){return <BrowserRouter basename={APP_BASE_PATH}><AuthProvider><ToastProvider><Routes>
  <Route path="/login" element={<AuthPage/>}/><Route path="/accept-invitation" element={<Navigate to="/login" replace/>}/><Route path="/reset-password" element={<Navigate to="/login" replace/>}/>
  <Route element={<Protected/>}><Route element={<AppLayout/>}>
    <Route index element={<Dashboard/>}/><Route path="assignments" element={<AssignmentsPage/>}/><Route path="assignments/:id" element={<AssignmentDetail/>}/><Route path="submissions" element={<SubmissionsPage/>}/><Route path="submissions/:id" element={<SubmissionDetail/>}/><Route path="performance" element={<PerformancePage/>}/><Route path="reports" element={<ReportsPage/>}/><Route path="reports/:id" element={<ReportDetail/>}/><Route path="leaderboard" element={<LeaderboardPage/>}/><Route path="notifications" element={<NotificationsPage/>}/><Route path="profile" element={<ProfilePage/>}/>
    <Route element={<Protected role={['admin','sales','trainer']}/>}> <Route path="batches" element={<BatchesPage/>}/><Route path="students" element={<StudentsPage/>}/><Route path="students/:id" element={<PerformancePage/>}/><Route path="courses" element={<CoursesPage/>}/><Route path="topics" element={<CoursesPage topics/>}/></Route><Route element={<Protected role={['admin','sales']}/>}> <Route path="team" element={<StaffPage/>}/></Route><Route element={<Protected role="trainer"/>}><Route path="materials" element={<MaterialsPage/>}/><Route path="generator" element={<GeneratorPage/>}/><Route path="assignments/new" element={<AssignmentEditor/>}/><Route path="assignments/:id/edit" element={<AssignmentEditor/>}/><Route path="settings" element={<SettingsPage/>}/></Route>
    <Route element={<Protected role="student"/>}><Route path="workspace/:id" element={<Workspace/>}/><Route path="coding" element={<AssignmentsPage coding/>}/><Route path="learning-path" element={<LearningPath/>}/></Route>
    <Route path="*" element={<Empty title="This page couldn’t be found" description="Choose a page from the navigation to continue."/>}/>
  </Route></Route></Routes></ToastProvider></AuthProvider></BrowserRouter>;}
