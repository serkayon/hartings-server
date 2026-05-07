import { BrowserRouter, Routes, Route ,Navigate} from 'react-router-dom'
import MonitoringDashboard from './components/MonitoringDashboard'
import PerformanceAnalytics from './components/PerformanceAnalytics'
import MenuPage from './components/MenuPage'
import KPI from './components/KPI'
import Settings from './components/Settings'
import Report from './components/Report'
function App() {
  return (
    <BrowserRouter>
      <div className="w-full min-h-screen">
        <Routes>
          <Route path="/" element={<MonitoringDashboard />} />
          <Route path="/analytics" element={<PerformanceAnalytics />} />
          
          <Route path="/menu" element={<MenuPage />}>
            <Route index element={<Navigate to="report" replace />} />
            <Route path="report" element={<Report />} />
            <Route path="kpi" element={<KPI />} />
            <Route path="settings" element={<Settings />} />
</Route>

        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
