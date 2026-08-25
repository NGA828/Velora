import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  BarChart3,
  Bell,
  Boxes,
  BrainCircuit,
  Building2,
  CreditCard,
  ClipboardList,
  FileText,
  HeartHandshake,
  Home,
  Hospital,
  LogOut,
  Menu,
  MessagesSquare,
  Pill,
  PhoneCall,
  ReceiptText,
  ScrollText,
  Send,
  Settings,
  ShieldCheck,
  Stethoscope,
  UserRound,
  UsersRound,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { logout } from '../../modules/auth/api/auth-api'
import { sessionQueryKey, useSession } from '../../modules/auth/hooks/use-session'
import { useUnreadNotificationCount } from '../../modules/notifications/use-unread-notifications'
import { AppApiError } from '../../shared/api/errors'
import { CallOverlay } from '../../shared/calls/CallOverlay'
import { NotificationToasts } from '../../shared/notifications/NotificationToasts'
import { RealtimeProvider } from '../providers/RealtimeProvider'
import { Button } from '../../shared/ui/actions/Button'
import { Alert } from '../../shared/ui/feedback/Alert'
import { Brand } from '../../shared/ui/navigation/Brand'

const defaultNavigation = [
  { to: '/', label: 'Workspace', icon: Home, end: true },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const doctorNavigation = [
  { to: '/doctor', label: 'Dashboard', icon: Home, end: true },
  { to: '/doctor/patients', label: 'Patients', icon: ClipboardList, end: false },
  { to: '/doctor/medical-files', label: 'Medical files', icon: FileText, end: false },
  { to: '/doctor/prescriptions', label: 'Prescriptions', icon: Pill, end: false },
  { to: '/doctor/monitoring', label: 'Patient monitoring', icon: MessagesSquare, end: false },
  { to: '/doctor/icu-recommendations', label: 'ICU recommendations', icon: BrainCircuit, end: false },
  { to: '/doctor/transfers', label: 'Transfer requests', icon: Send, end: false },
  { to: '/doctor/death-certificates', label: 'Death certificates', icon: ScrollText, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const nurseNavigation = [
  { to: '/nurse', label: 'Dashboard', icon: Home, end: true },
  { to: '/nurse/patients', label: 'My patients', icon: ClipboardList, end: false },
  { to: '/nurse/vital-signs', label: 'Vital signs', icon: Activity, end: false },
  { to: '/nurse/medication', label: 'Medication', icon: Pill, end: false },
  { to: '/nurse/patient-guards', label: 'Patient Guards', icon: ShieldCheck, end: false },
  { to: '/nurse/icu-recommendations', label: 'ICU recommendations', icon: BrainCircuit, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const patientGuardNavigation = [
  { to: '/patient-guard', label: 'Dashboard', icon: Home, end: true },
  { to: '/patient-guard/patients', label: 'Patient information', icon: HeartHandshake, end: false },
  { to: '/patient-guard/medical-files', label: 'Medical files', icon: FileText, end: false },
  { to: '/patient-guard/prescriptions', label: 'Prescriptions', icon: Pill, end: false },
  { to: '/patient-guard/monitoring', label: 'Monitoring', icon: MessagesSquare, end: false },
  { to: '/patient-guard/transfers', label: 'Transfer requests', icon: Send, end: false },
  { to: '/patient-guard/death-certificates', label: 'Death certificate', icon: ScrollText, end: false },
  { to: '/patient-guard/billing', label: 'Billing', icon: ReceiptText, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const accountingNavigation = [
  { to: '/accounting', label: 'Dashboard', icon: Home, end: true },
  { to: '/accounting/billing', label: 'Billing', icon: ReceiptText, end: false },
  { to: '/accounting/payments', label: 'Payments', icon: CreditCard, end: false },
  { to: '/accounting/reports', label: 'Reports', icon: BarChart3, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const adminNavigation = [
  { to: '/admin-system', label: 'Dashboard', icon: Settings, end: true },
  { to: '/admin-system/users', label: 'Users', icon: UsersRound, end: false },
  { to: '/admin-system/audit', label: 'Audit & monitoring', icon: ShieldCheck, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

const headOfServiceNavigation = [
  { to: '/head-of-service', label: 'Dashboard', icon: Home, end: true },
  { to: '/head-of-service/personnel', label: 'Medical personnel', icon: UsersRound, end: false },
  { to: '/head-of-service/hospital-information', label: 'Hospital information', icon: Building2, end: false },
  { to: '/head-of-service/specialties', label: 'Specialties', icon: Stethoscope, end: false },
  { to: '/head-of-service/resources', label: 'Resources & services', icon: Boxes, end: false },
  { to: '/head-of-service/medications', label: 'Medications', icon: Pill, end: false },
  { to: '/head-of-service/external-hospitals', label: 'External hospitals', icon: Hospital, end: false },
  { to: '/head-of-service/clinical-rules', label: 'Clinical rules', icon: Activity, end: false },
  { to: '/head-of-service/reports', label: 'Reports', icon: BarChart3, end: false },
  { to: '/messages', label: 'Messages', icon: MessagesSquare, end: false },
  { to: '/calls', label: 'Calls', icon: PhoneCall, end: false },
  { to: '/notifications', label: 'Notifications', icon: Bell, end: false },
  { to: '/profile', label: 'Profile & security', icon: UserRound, end: false },
]

export function HospitalShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  const session = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: sessionQueryKey })
      navigate('/login', { replace: true })
    },
  })
  const user = session.data!.user
  const unreadNotifications = useUnreadNotificationCount()
  const navigation = user.role === 'ADMIN'
    ? adminNavigation
    : user.role === 'ACCOUNTING'
      ? accountingNavigation
      : user.role === 'HEAD_OF_SERVICE'
        ? headOfServiceNavigation
        : user.role === 'DOCTOR'
      ? doctorNavigation
      : user.role === 'NURSE'
        ? nurseNavigation
        : user.role === 'PATIENT_GUARD'
          ? patientGuardNavigation
          : defaultNavigation
  const initials = `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase()

  return (
    <div className="hospital-shell">
      <RealtimeProvider userId={user.id} />
      <CallOverlay userId={user.id} />
      <NotificationToasts />
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="mobile-topbar">
        <Brand />
        <button
          type="button"
          className="icon-button"
          onClick={() => setMenuOpen((current) => !current)}
          aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X /> : <Menu />}
        </button>
      </header>

      {menuOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <aside className={`sidebar ${menuOpen ? 'sidebar--open' : ''}`}>
        <div className="sidebar__brand"><Brand /></div>
        <div className="sidebar__context">
          <span>Signed in as</span>
          <strong>{user.role_label}</strong>
        </div>
        <nav className="sidebar__nav" aria-label="Primary navigation">
          <p>Workspace</p>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link'}
            >
              <Icon size={19} aria-hidden="true" />
              <span>{label}</span>
              {label === 'Notifications' && unreadNotifications > 0 && (
                <span className="sidebar__badge" aria-label={`${unreadNotifications} unread notifications`}>
                  {unreadNotifications > 99 ? '99+' : unreadNotifications}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__account">
          <span className="avatar" aria-hidden="true">{initials}</span>
          <span className="sidebar__account-copy">
            <strong>{user.full_name}</strong>
            <small>{user.email}</small>
          </span>
          <button
            type="button"
            className="icon-button icon-button--subtle"
            aria-label="Sign out"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <div className="shell-content">
        {logoutMutation.error && (
          <div className="shell-alert">
            <Alert tone="critical" title="Sign out was not completed">
              {logoutMutation.error instanceof AppApiError
                ? logoutMutation.error.message
                : 'Try again.'}
            </Alert>
            <Button variant="ghost" onClick={() => logoutMutation.reset()}>Dismiss</Button>
          </div>
        )}
        <main id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
