import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(1, 'Enter your password.'),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const invitationSchema = z
  .object({
    first_name: z.string().trim().min(1, 'Enter your first name.').max(80),
    last_name: z.string().trim().min(1, 'Enter your last name.').max(80),
    phone: z.string().trim().max(32).optional(),
    password: z.string().min(12, 'Use at least 12 characters.'),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'The passwords do not match.',
    path: ['confirm_password'],
  })

export type InvitationFormValues = z.infer<typeof invitationSchema>

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, 'Enter your current password.'),
    new_password: z.string().min(12, 'Use at least 12 characters.'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'The passwords do not match.',
    path: ['confirm_password'],
  })

export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>
