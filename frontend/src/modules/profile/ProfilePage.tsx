import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Camera, Mail, ShieldCheck, UserRound } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { AppApiError } from '../../shared/api/errors'
import { Button } from '../../shared/ui/actions/Button'
import { Alert } from '../../shared/ui/feedback/Alert'
import { FormField } from '../../shared/ui/forms/FormField'
import { sessionQueryKey, useSession } from '../auth/hooks/use-session'
import { updateProfile } from '../auth/api/auth-api'

export function ProfilePage() {
  const { data } = useSession()
  const user = data!.user
  const client = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const [first_name, setFirstName] = useState(user.first_name)
  const [last_name, setLastName] = useState(user.last_name)
  const [phone, setPhone] = useState(user.phone)
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [formError, setFormError] = useState('')

  useEffect(() => {
    document.title = 'Profile & security · Velora'
  }, [])

  // Keep the form in sync if the session refreshes elsewhere.
  useEffect(() => {
    setFirstName(user.first_name)
    setLastName(user.last_name)
    setPhone(user.phone)
  }, [user.first_name, user.last_name, user.phone])

  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: (session) => {
      client.setQueryData(sessionQueryKey, session)
      setAvatarFile(null)
      setPreviewUrl(null)
      setFormError('')
    },
    onError: (error: unknown) => {
      setFormError(error instanceof AppApiError ? error.message : 'Could not save your profile.')
    },
  })

  const pickAvatar = (file: File | undefined) => {
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setFormError('Use a JPEG, PNG or WebP image for your profile picture.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setFormError('Profile picture must be 5 MB or smaller.')
      return
    }
    setFormError('')
    setAvatarFile(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  const avatarSrc = previewUrl ?? user.avatar_url ?? null

  return (
    <div className="workspace-page workspace-page--narrow">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Profile & security</h1>
          <p>Edit your personal information and profile picture.</p>
        </div>
      </header>

      {formError && <Alert tone="critical">{formError}</Alert>}
      {mutation.isSuccess && !formError && (
        <Alert tone="success" title="Profile saved">
          Your changes are now visible across Velora.
        </Alert>
      )}

      <form
        className="profile-card"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate({ first_name, last_name, phone, avatar: avatarFile ?? undefined })
        }}
      >
        <div className="profile-card__identity">
          <button
            type="button"
            className="profile-card__avatar profile-card__avatar--editable"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Upload profile picture"
            title="Upload profile picture"
          >
            {avatarSrc ? <img src={avatarSrc} alt="Your profile" /> : <UserRound aria-hidden="true" />}
            <span className="profile-card__camera"><Camera size={13} /></span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="visually-hidden"
            onChange={(event) => pickAvatar(event.target.files?.[0])}
          />
          <div>
            <h2>{user.full_name}</h2>
            <p>{user.role_label}</p>
          </div>
          <span className="status-pill status-pill--success">Active</span>
        </div>

        <div className="profile-form-grid">
          <FormField
            label="First name"
            value={first_name}
            onChange={(event) => setFirstName(event.target.value)}
            required
          />
          <FormField
            label="Last name"
            value={last_name}
            onChange={(event) => setLastName(event.target.value)}
            required
          />
          <FormField
            label="Phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="+237 6XX XX XX XX"
          />
        </div>
        {avatarFile && (
          <p className="profile-avatar-hint">
            New picture ready — save to upload it{previewUrl ? '.' : ''}
          </p>
        )}

        <div className="profile-details">
          <div><dt><Mail size={17} /> Email address</dt><dd>{user.email}</dd></div>
          <div><dt><ShieldCheck size={17} /> Access role</dt><dd>{user.role_label}</dd></div>
        </div>

        <div className="profile-card__actions">
          <Button
            type="submit"
            isLoading={mutation.isPending}
            disabled={!first_name.trim() || !last_name.trim()}
          >
            Save changes
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setFirstName(user.first_name)
              setLastName(user.last_name)
              setPhone(user.phone)
              setAvatarFile(null)
              setPreviewUrl(null)
              setFormError('')
            }}
          >
            Discard changes
          </Button>
        </div>
      </form>

      <section className="section-panel security-panel">
        <div>
          <p className="eyebrow">Password</p>
          <h2>Keep your access private</h2>
          <p>Change your password if it may have been seen or reused elsewhere.</p>
        </div>
        <Link className="button button--secondary" to="/change-password">Change password</Link>
      </section>
    </div>
  )
}
