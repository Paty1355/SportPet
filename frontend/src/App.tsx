import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Camera, Dumbbell, Salad, User } from 'lucide-react'
import { AppShell } from './app/AppShell'
import { CalendarPage } from './features/calendar/CalendarPage'
import { ComingSoonPage } from './features/placeholders/ComingSoonPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<CalendarPage />} />
          <Route
            path="/trening"
            element={
              <ComingSoonPage
                title="Training agent"
                description="Build a workout plan with the help of the agent. The result goes straight to your calendar."
                icon={Dumbbell}
              />
            }
          />
          <Route
            path="/maszyny"
            element={
              <ComingSoonPage
                title="Machine recognition"
                description="Point the camera at a gym machine and we'll suggest exercises and settings."
                icon={Camera}
              />
            }
          />
          <Route
            path="/dieta"
            element={
              <ComingSoonPage
                title="Diet agent"
                description="A meal and calorie plan matched to your workouts."
                icon={Salad}
              />
            }
          />
          <Route
            path="/profil"
            element={
              <ComingSoonPage
                title="Profile and stats"
                description="Your progress, charts and summaries in one place."
                icon={User}
              />
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
