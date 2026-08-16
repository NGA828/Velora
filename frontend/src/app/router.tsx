import { createBrowserRouter } from 'react-router-dom'

import { NotFoundPage } from './error-boundaries/NotFoundPage'
import { RequirePasswordReady } from './guards/RequirePasswordReady'
import { RequireRole } from './guards/RequireRole'
import { SessionGate } from './guards/SessionGate'
import { HospitalShell } from './layouts/HospitalShell'
import { WorkspaceHomePage } from './WorkspaceHomePage'

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: async () => ({
      Component: (await import('../modules/auth/pages/LoginPage')).LoginPage,
    }),
  },
  {
    path: '/accept-invitation',
    lazy: async () => ({
      Component: (await import('../modules/auth/pages/AcceptInvitationPage')).AcceptInvitationPage,
    }),
  },
  {
    element: <SessionGate />,
    children: [
      {
        path: '/change-password',
        lazy: async () => ({
          Component: (await import('../modules/auth/pages/ChangePasswordPage')).ChangePasswordPage,
        }),
      },
      {
        element: <RequirePasswordReady />,
        children: [
          {
            element: <HospitalShell />,
            children: [
              { index: true, element: <WorkspaceHomePage /> },
              {
                element: <RequireRole roles={['HEAD_OF_SERVICE']} />,
                children: [
                  {
                    path: '/head-of-service',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/dashboard/DashboardPage')).HeadOfServiceDashboardPage,
                    }),
                  },
                  {
                    path: '/head-of-service/personnel',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/medical-personnel/MedicalPersonnelPage')).MedicalPersonnelPage,
                    }),
                  },
                  {
                    path: '/head-of-service/hospital-information',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/hospital-information/HospitalInformationPage')).HospitalInformationPage,
                    }),
                  },
                  {
                    path: '/head-of-service/specialties',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/specialties/SpecialtiesPage')).SpecialtiesPage,
                    }),
                  },
                  {
                    path: '/head-of-service/resources',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/resources/ResourcesPage')).ResourcesPage,
                    }),
                  },
                  {
                    path: '/head-of-service/medications',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/medications/MedicationsPage')).MedicationsPage,
                    }),
                  },
                  {
                    path: '/head-of-service/external-hospitals',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/external-hospitals/ExternalHospitalsPage')).ExternalHospitalsPage,
                    }),
                  },
                  {
                    path: '/head-of-service/clinical-rules',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/clinical-rules/ClinicalRulesPage')).ClinicalRulesPage,
                    }),
                  },
                  {
                    path: '/head-of-service/reports',
                    lazy: async () => ({
                      Component: (await import('../modules/head-of-service/reports/OperationalReportsPage')).OperationalReportsPage,
                    }),
                  },
                ],
              },
              {
                element: <RequireRole roles={['DOCTOR']} />,
                children: [
                  {
                    path: '/doctor',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/dashboard/DoctorDashboardPage')).DoctorDashboardPage,
                    }),
                  },
                  {
                    path: '/doctor/patients',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/patients/DoctorPatientsPage')).DoctorPatientsPage,
                    }),
                  },
                  {
                    path: '/doctor/patients/new',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/patients/RegisterPatientPage')).RegisterPatientPage,
                    }),
                  },
                  {
                    path: '/doctor/patients/:patientId',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/patients/DoctorPatientDetailPage')).DoctorPatientDetailPage,
                    }),
                  },
                  {
                    path: '/doctor/medical-files',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/medical-files/DoctorMedicalFilesPage')).DoctorMedicalFilesPage,
                    }),
                  },
                  {
                    path: '/doctor/patients/:patientId/medical-file',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/medical-files/DoctorMedicalFilePage')).DoctorMedicalFilePage,
                    }),
                  },
                  {
                    path: '/doctor/patients/:patientId/vitals',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/vital-signs/DoctorVitalHistoryPage')).DoctorVitalHistoryPage,
                    }),
                  },
                  {
                    path: '/doctor/prescriptions',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/prescriptions/DoctorPrescriptionsPage')).DoctorPrescriptionsPage,
                    }),
                  },
                  {
                    path: '/doctor/prescriptions/new',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/prescriptions/CreatePrescriptionPage')).CreatePrescriptionPage,
                    }),
                  },
                  {
                    path: '/doctor/patients/:patientId/prescriptions',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/prescriptions/DoctorPrescriptionsPage')).DoctorPrescriptionsPage,
                    }),
                  },
                  {
                    path: '/doctor/monitoring',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/monitoring/DoctorMonitoringPage')).DoctorMonitoringPage,
                    }),
                  },
                  {
                    path: '/doctor/transfers',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/transfers/DoctorTransfersPage')).DoctorTransfersPage,
                    }),
                  },
                  {
                    path: '/doctor/death-certificates',
                    lazy: async () => ({
                      Component: (await import('../modules/doctor/death-certificates/DoctorDeathCertificatesPage')).DoctorDeathCertificatesPage,
                    }),
                  },
                ],
              },
              {
                element: <RequireRole roles={['NURSE']} />,
                children: [
                  {
                    path: '/nurse',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/dashboard/NurseDashboardPage')).NurseDashboardPage,
                    }),
                  },
                  {
                    path: '/nurse/patients',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/patients/NursePatientsPage')).NursePatientsPage,
                    }),
                  },
                  {
                    path: '/nurse/patients/:patientId',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/patients/NursePatientDetailPage')).NursePatientDetailPage,
                    }),
                  },
                  {
                    path: '/nurse/patients/:patientId/medical-file',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/patients/NurseMedicalFilePage')).NurseMedicalFilePage,
                    }),
                  },
                  {
                    path: '/nurse/vital-signs',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/vital-signs/NurseVitalSignsPage')).NurseVitalSignsPage,
                    }),
                  },
                  {
                    path: '/nurse/patients/:patientId/vitals',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/vital-signs/NurseVitalHistoryPage')).NurseVitalHistoryPage,
                    }),
                  },
                  {
                    path: '/nurse/patients/:patientId/vitals/new',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/vital-signs/RecordVitalSignsPage')).RecordVitalSignsPage,
                    }),
                  },
                  {
                    path: '/nurse/medication',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/medication/MedicationPage')).MedicationPage,
                    }),
                  },
                  {
                    path: '/nurse/patient-guards',
                    lazy: async () => ({
                      Component: (await import('../modules/nurse/patient-guards/PatientGuardsPage')).PatientGuardsPage,
                    }),
                  },
                ],
              },
              {
                element: <RequireRole roles={['PATIENT_GUARD']} />,
                children: [
                  {
                    path: '/patient-guard',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/dashboard/PatientGuardDashboardPage')).PatientGuardDashboardPage,
                    }),
                  },
                  {
                    path: '/patient-guard/patients',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/patient-information/PatientInformationPage')).PatientInformationPage,
                    }),
                  },
                  {
                    path: '/patient-guard/patients/:patientId',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/patient-information/PatientGuardPatientDetailPage')).PatientGuardPatientDetailPage,
                    }),
                  },
                  {
                    path: '/patient-guard/medical-files',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/medical-files/PatientGuardMedicalFilesPage')).PatientGuardMedicalFilesPage,
                    }),
                  },
                  {
                    path: '/patient-guard/patients/:patientId/medical-file',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/medical-files/PatientGuardMedicalFilePage')).PatientGuardMedicalFilePage,
                    }),
                  },
                  {
                    path: '/patient-guard/prescriptions',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/prescriptions/PatientGuardPrescriptionsPage')).PatientGuardPrescriptionsPage,
                    }),
                  },
                  {
                    path: '/patient-guard/monitoring',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/monitoring/PatientGuardMonitoringPage')).PatientGuardMonitoringPage,
                    }),
                  },
                  {
                    path: '/patient-guard/transfers',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/transfers/PatientGuardTransfersPage')).PatientGuardTransfersPage,
                    }),
                  },
                  {
                    path: '/patient-guard/death-certificates',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/death-certificates/PatientGuardDeathCertificatesPage')).PatientGuardDeathCertificatesPage,
                    }),
                  },
                  {
                    path: '/patient-guard/billing',
                    lazy: async () => ({
                      Component: (await import('../modules/patient-guard/billing/PatientGuardBillingPage')).PatientGuardBillingPage,
                    }),
                  },
                ],
              },
              {
                element: <RequireRole roles={['ACCOUNTING']} />,
                children: [
                  {
                    path: '/accounting',
                    lazy: async () => ({
                      Component: (await import('../modules/accounting/dashboard/AccountingDashboardPage')).AccountingDashboardPage,
                    }),
                  },
                  {
                    path: '/accounting/billing',
                    lazy: async () => ({
                      Component: (await import('../modules/accounting/billing/BillingPage')).BillingPage,
                    }),
                  },
                  {
                    path: '/accounting/payments',
                    lazy: async () => ({
                      Component: (await import('../modules/accounting/payments/PaymentsPage')).PaymentsPage,
                    }),
                  },
                  {
                    path: '/accounting/reports',
                    lazy: async () => ({
                      Component: (await import('../modules/accounting/reports/FinancialReportsPage')).FinancialReportsPage,
                    }),
                  },
                ],
              },
              {
                element: <RequireRole roles={['ADMIN']} />,
                children: [
                  {
                    path: '/admin-system',
                    lazy: async () => ({
                      Component: (await import('../modules/admin/dashboard/AdminDashboardPage')).AdminDashboardPage,
                    }),
                  },
                  {
                    path: '/admin-system/users',
                    lazy: async () => ({
                      Component: (await import('../modules/admin/users/AdminUsersPage')).AdminUsersPage,
                    }),
                  },
                  {
                    path: '/admin-system/audit',
                    lazy: async () => ({
                      Component: (await import('../modules/admin/audit/AdminAuditPage')).AdminAuditPage,
                    }),
                  },
                ],
              },
              {
                path: '/messages',
                lazy: async () => ({
                  Component: (await import('../modules/messages/MessagesPage')).MessagesPage,
                }),
              },
              {
                path: '/calls',
                lazy: async () => ({
                  Component: (await import('../modules/calls/CallsPage')).CallsPage,
                }),
              },
              {
                path: '/notifications',
                lazy: async () => ({
                  Component: (await import('../modules/notifications/NotificationsPage')).NotificationsPage,
                }),
              },
              {
                path: '/profile',
                lazy: async () => ({
                  Component: (await import('../modules/profile/ProfilePage')).ProfilePage,
                }),
              },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
