import type { UserRole } from '../../modules/auth/types/session'

interface RoleContent {
  eyebrow: string
  heading: string
  description: string
}

export const roleContent: Record<UserRole, RoleContent> = {
  ADMIN: {
    eyebrow: 'System administration',
    heading: 'System control with clinical boundaries',
    description: 'Manage identity and platform health without automatic access to patient records.',
  },
  HEAD_OF_SERVICE: {
    eyebrow: 'Hospital operations',
    heading: 'Prepare the hospital for connected care',
    description: 'Staff, departments, resources and clinical configuration will be managed here.',
  },
  DOCTOR: {
    eyebrow: 'Clinical workspace',
    heading: 'Patient decisions, in the right context',
    description: 'Assigned patient care, monitoring, prescriptions and transfers will meet here.',
  },
  NURSE: {
    eyebrow: 'Care delivery',
    heading: 'Your assigned care, clearly prioritized',
    description: 'Patient monitoring, medication due work and Guard access will meet here.',
  },
  PATIENT_GUARD: {
    eyebrow: 'Patient support',
    heading: 'The patient information you are authorized to see',
    description: 'Questions, prescriptions and decisions will be kept connected and understandable.',
  },
  ACCOUNTING: {
    eyebrow: 'Financial operations',
    heading: 'Accurate billing without clinical exposure',
    description: 'Charges, invoices and payments will be managed within strict information boundaries.',
  },
}

export const capabilityLabels: Record<string, string> = {
  'users.manage': 'Manage system users',
  'system.manage': 'Manage system configuration',
  'audit.security.read': 'Review security audit',
  'staff.manage': 'Manage medical personnel',
  'hospital.manage': 'Manage hospital information',
  'vital_rules.manage': 'Manage clinical rule sets',
  'reports.operational.read': 'View operational reports',
  'patients.register': 'Register patients',
  'patients.assigned.read': 'Access assigned patients',
  'medical_records.clinical.manage': 'Manage assigned medical records',
  'prescriptions.manage': 'Create and manage prescriptions',
  'monitoring.manage': 'Manage patient monitoring',
  'transfers.manage': 'Manage transfer requests',
  'death_certificates.manage': 'Issue death certificates',
  'patient_guards.manage': 'Manage Patient Guard access',
  'vitals.record': 'Record vital signs',
  'medication.administer': 'Confirm medication administration',
  'patients.linked.read': 'View linked patient information',
  'monitoring.respond': 'Respond to monitoring questions',
  'prescriptions.linked.read': 'View authorized prescriptions',
  'transfers.decide': 'Review transfer requests',
  'death_certificates.issued.read': 'View issued certificates',
  'billing.manage': 'Manage billing and payments',
  'reports.financial.read': 'View financial reports',
}
