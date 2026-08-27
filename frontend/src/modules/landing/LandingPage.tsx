import {
  Activity,
  ArrowRight,
  BellRing,
  BrainCircuit,
  Check,
  ClipboardList,
  HeartHandshake,
  HeartPulse,
  Lock,
  Menu,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useSession } from '../auth/hooks/use-session'
import { useCountUp, useParallax, useReveal, useTilt } from './landing-hooks'
import './landing.css'

import careTeamImage from '../../assets/landing/care-team.png'
import guardianImage from '../../assets/landing/guardian.png'
import heroDashboardImage from '../../assets/landing/hero-dashboard.png'
import icuMonitoringImage from '../../assets/landing/icu-monitoring.png'

function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const { ref, visible } = useReveal<HTMLDivElement>()
  return (
    <div
      ref={ref}
      className={`lp-reveal ${visible ? 'lp-reveal--visible' : ''} ${className}`}
      style={{ '--reveal-delay': `${delay}ms` } as React.CSSProperties}
    >
      {children}
    </div>
  )
}

function Stat({ value, suffix, label }: { value: number; suffix?: string; label: string }) {
  const { ref, value: animated } = useCountUp(value)
  return (
    <div className="lp-stat">
      <strong>
        <span ref={ref}>{animated}</span>
        {suffix}
      </strong>
      <span>{label}</span>
    </div>
  )
}

const NAV_LINKS = [
  { href: '#platform', label: 'Platform' },
  { href: '#assistant', label: 'AI Assistant' },
  { href: '#workflow', label: 'How it works' },
  { href: '#roles', label: 'Care team' },
]

const MARQUEE_ITEMS = [
  'Central Regional Hospital',
  'University Teaching Hospital',
  'Lakeside Medical Center',
  'St. Mary\u2019s Clinic',
  'Emergency & Critical Care Unit',
  'Mother & Child Center',
  'General Regional Hospital',
  'Unity Health Clinic',
]

const ROLES = [
  { icon: Stethoscope, label: 'Head of Service' },
  { icon: HeartPulse, label: 'Doctors' },
  { icon: Activity, label: 'Nurses' },
  { icon: HeartHandshake, label: 'Patient Guards' },
  { icon: ClipboardList, label: 'Accounting' },
  { icon: ShieldCheck, label: 'Administrators' },
]

export function LandingPage() {
  const session = useSession()
  const isAuthenticated = Boolean(session.data?.user)
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const heroTiltRef = useTilt<HTMLDivElement>(7)
  const parallaxRef = useParallax<HTMLDivElement>(30)

  useEffect(() => {
    document.title = 'Velora · Intelligent Hospital Care Coordination'
  }, [])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="landing">
      {/* ------------------------------- Navigation ------------------------------ */}
      <header className={`landing-nav ${scrolled ? 'landing-nav--scrolled' : ''}`}>
        <div className="landing__container landing-nav__inner">
          <Link to="/" className="landing-brand">
            <span className="landing-brand__mark">
              <HeartPulse size={18} />
            </span>
            <span>
              Velora
              <small>Hospital workspace</small>
            </span>
          </Link>

          <nav className="landing-nav__links" aria-label="Landing sections">
            {NAV_LINKS.map((link) => (
              <a key={link.href} href={link.href}>
                {link.label}
              </a>
            ))}
          </nav>

          <div className="landing-nav__cta">
            {isAuthenticated ? (
              <Link to="/workspace" className="lp-button lp-button--primary">
                Open workspace <ArrowRight size={16} />
              </Link>
            ) : (
              <>
                <Link to="/login" className="lp-button lp-button--ghost">
                  Log in
                </Link>
                <a href="#platform" className="lp-button lp-button--primary">
                  Explore the platform
                </a>
              </>
            )}
            <button
              type="button"
              className="lp-button lp-button--ghost"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              onClick={() => setMenuOpen((open) => !open)}
              style={{ padding: '10px 14px' }}
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <div className="landing__container" style={{ paddingTop: 12 }}>
            <nav
              aria-label="Landing sections (mobile)"
              style={{ display: 'grid', gap: 14, background: '#fff', borderRadius: 16, padding: '18px 20px', boxShadow: '0 16px 40px rgb(13 59 79 / 12%)' }}
            >
              {NAV_LINKS.map((link) => (
                <a key={link.href} href={link.href} onClick={() => setMenuOpen(false)} style={{ color: 'var(--landing-ink)' }}>
                  {link.label}
                </a>
              ))}
              <Link to={isAuthenticated ? '/workspace' : '/login'} onClick={() => setMenuOpen(false)} style={{ color: 'var(--landing-teal)', fontWeight: 650 }}>
                {isAuthenticated ? 'Open workspace' : 'Log in'}
              </Link>
            </nav>
          </div>
        )}
      </header>

      {/* --------------------------------- Hero ---------------------------------- */}
      <section className="lp-hero">
        <div className="lp-hero__grid-bg" ref={parallaxRef} />
        <div className="lp-hero__orb lp-hero__orb--one" />
        <div className="lp-hero__orb lp-hero__orb--two" />

        <div className="landing__container lp-hero__inner">
          <div>
            <Reveal>
              <span className="lp-hero__eyebrow">
                <span className="lp-pulse-dot" />
                Clinical decision support · Now with an AI assistant
              </span>
            </Reveal>
            <Reveal delay={90}>
              <h1 className="lp-hero__title">
                ICU-grade clarity for every patient, <em>even when specialists are stretched.</em>
              </h1>
            </Reveal>
            <Reveal delay={180}>
              <p className="lp-hero__sub">
                Velora watches every vital sign, applies your hospital&apos;s own clinical rules, and
                produces explainable ICU recommendations in real time — then its conversational
                assistant explains them in plain language to doctors, nurses, and guardians.
              </p>
            </Reveal>
            <Reveal delay={260}>
              <div className="lp-hero__actions">
                <Link to={isAuthenticated ? '/workspace' : '/login'} className="lp-button lp-button--primary">
                  {isAuthenticated ? 'Open your workspace' : 'Log in to your workspace'} <ArrowRight size={16} />
                </Link>
                <a href="#workflow" className="lp-button lp-button--ghost">
                  See how it works
                </a>
              </div>
            </Reveal>
            <Reveal delay={340}>
              <div className="lp-hero__proof">
                <ShieldCheck size={16} />
                Role-scoped access · Full audit trail · Session-secured
              </div>
            </Reveal>
          </div>

          <div className="lp-hero__visual">
            <div className="lp-hero__card" ref={heroTiltRef}>
              <img src={heroDashboardImage} alt="Velora patient monitoring dashboard with live vital signs and ICU recommendation panel" />
            </div>

            <div className="lp-float-card lp-float-card--vitals">
              <span className="lp-float-card__icon lp-float-card__icon--heart">
                <HeartPulse size={18} />
              </span>
              <div>
                <small>Heart rate · live</small>
                <strong>72 BPM</strong>
                <svg className="lp-float-card__spark" viewBox="0 0 74 26" aria-hidden="true">
                  <path
                    d="M1 14 L8 14 L12 6 L16 22 L20 10 L26 14 L36 14 L40 5 L44 23 L48 12 L54 14 L73 14"
                    fill="none"
                    stroke="#b93845"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
            </div>

            <div className="lp-float-card lp-float-card--icu">
              <span className="lp-float-card__icon lp-float-card__icon--brain">
                <BrainCircuit size={18} />
              </span>
              <div>
                <small>ICU recommendation</small>
                <strong>Assessment advised</strong>
                <small style={{ textTransform: 'none', letterSpacing: 0 }}>
                  3 criteria matched · specialist limited
                </small>
              </div>
            </div>
          </div>
        </div>

        <svg className="lp-ecg" viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 60 H240 L260 60 L272 18 L288 78 L300 42 L312 60 H560 L580 60 L592 18 L608 78 L620 42 L632 60 H900 L920 60 L932 18 L948 78 L960 42 L972 60 H1240 L1260 60 L1272 18 L1288 78 L1300 42 L1312 60 H1440" />
        </svg>
      </section>

      {/* -------------------------------- Marquee -------------------------------- */}
      <div className="lp-marquee" aria-hidden="true">
        <div className="lp-marquee__track">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, index) => (
            <span className="lp-marquee__item" key={`${item}-${index}`}>
              <HeartPulse size={14} />
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* --------------------------------- Stats --------------------------------- */}
      <section className="lp-section" id="impact">
        <div className="landing__container">
          <Reveal>
            <div className="lp-stats">
              <Stat value={24} suffix="/7" label="Continuous patient monitoring" />
              <Stat value={100} suffix="%" label="Clinical actions audited" />
              <Stat value={6} label="Role-scoped workspaces" />
              <Stat value={1} suffix="s" label="Vital-sign rule evaluation" />
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------- Features -------------------------------- */}
      <section className="lp-section lp-section--alt" id="platform">
        <div className="landing__container">
          <Reveal>
            <div className="lp-section__head">
              <span className="lp-section__eyebrow">The platform</span>
              <h2 className="lp-section__title">
                Deterministic clinical intelligence, humane communication
              </h2>
              <p className="lp-section__sub">
                The ICU Recommendation Engine makes the structured assessment. The AI assistant
                explains it. Both stay inside your hospital&apos;s privacy boundaries.
              </p>
            </div>
          </Reveal>

          <div className="lp-bento">
            <Reveal className="lp-bento__cell--wide" delay={60}>
              <article className="lp-bento__cell lp-bento__cell--wide">
                <span className="lp-bento__icon">
                  <BrainCircuit size={22} />
                </span>
                <h3>ICU Recommendation Engine</h3>
                <p>
                  Configurable clinical rules classify every patient as stable, unstable, or
                  critical. When ICU criteria match, Velora weighs specialist availability, ICU
                  beds, and hospital capacity — then delivers an explainable recommendation that
                  shows exactly which thresholds fired.
                </p>
              </article>
            </Reveal>

            <Reveal delay={140}>
              <article className="lp-bento__cell">
                <span className="lp-bento__icon">
                  <Sparkles size={22} />
                </span>
                <h3>Conversational assistant</h3>
                <p>
                  An AI layer that answers questions and explains recommendations in the language
                  each role understands — from clinician detail to plain words for guardians.
                </p>
              </article>
            </Reveal>

            <Reveal className="lp-bento__cell--wide" delay={80}>
              <article className="lp-bento__cell lp-bento__cell--media lp-bento__cell--wide">
                <img src={icuMonitoringImage} alt="Intensive care monitor showing live ECG and oxygen waveforms" />
                <div className="lp-bento__media-caption">
                  <h3>Live vital-sign monitoring</h3>
                  <p>Heart rate, SpO₂, blood pressure, temperature, and respiration — evaluated the moment they are recorded.</p>
                </div>
              </article>
            </Reveal>

            <Reveal delay={160}>
              <article className="lp-bento__cell">
                <span className="lp-bento__icon">
                  <Lock size={22} />
                </span>
                <h3>Privacy by architecture</h3>
                <p>
                  Server-side sessions, role-scoped data, guardian visibility flags, and a full
                  audit trail on every assistant answer.
                </p>
              </article>
            </Reveal>

            <Reveal delay={60}>
              <article className="lp-bento__cell">
                <span className="lp-bento__icon">
                  <BellRing size={22} />
                </span>
                <h3>Alerts &amp; escalation</h3>
                <p>
                  Critical vitals alert the right clinicians instantly — with transfers and
                  external hospital options when local resources run out.
                </p>
              </article>
            </Reveal>

            <Reveal className="lp-bento__cell--wide" delay={140}>
              <article className="lp-bento__cell lp-bento__cell--media lp-bento__cell--wide">
                <img src={guardianImage} alt="Family member using the Velora guardian app at a hospital bedside" />
                <div className="lp-bento__media-caption">
                  <h3>Built for guardians too</h3>
                  <p>Authorized Patient Guards follow care updates, prescriptions, and billing — and can ask the assistant what it all means.</p>
                </div>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ----------------------------- AI Assistant ------------------------------ */}
      <section className="lp-section" id="assistant">
        <div className="landing__container lp-assistant">
          <Reveal>
            <div className="lp-assistant__copy">
              <span className="lp-section__eyebrow">AI-powered, safety-guarded</span>
              <h2 className="lp-section__title" style={{ textAlign: 'left' }}>
                An assistant that explains — it never decides
              </h2>
              <p className="lp-section__sub" style={{ textAlign: 'left' }}>
                The assistant reads the patient information you are authorized to see and turns the
                official recommendation into a clear conversation.
              </p>
              <ul>
                <li>
                  <Check size={17} />
                  Explains which clinical criteria triggered an ICU assessment, in plain language.
                </li>
                <li>
                  <Check size={17} />
                  Answers role-appropriately: clinical detail for doctors and nurses, simple words
                  for guardians.
                </li>
                <li>
                  <Check size={17} />
                  Every answer is validated against the authorized clinical context and audited.
                </li>
                <li>
                  <Check size={17} />
                  Runs on free-tier AI providers, so conversations are not gated by per-message
                  costs.
                </li>
              </ul>
            </div>
          </Reveal>

          <Reveal delay={140}>
            <div className="lp-chat-demo" aria-label="Example conversation with the clinical assistant">
              <div className="lp-chat-demo__window">
                <div className="lp-chat-demo__header">
                  <span className="lp-chat-demo__avatar">
                    <BrainCircuit size={18} />
                  </span>
                  <div>
                    <strong style={{ fontSize: '0.95rem' }}>Care Information Assistant</strong>
                    <small>Authorized guardian view · Amina Biya</small>
                  </div>
                </div>
                <div className="lp-chat-msg lp-chat-msg--user">
                  Why is my mother being monitored so closely today?
                </div>
                <div className="lp-chat-typing" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="lp-chat-msg lp-chat-msg--bot">
                  Her latest recorded measurements show her condition currently needs close
                  observation. The care team has been alerted, and the clinical decision-support
                  system recommended an ICU assessment. Her nurse can walk you through the next
                  steps when you visit.
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------ How it works ----------------------------- */}
      <section className="lp-section lp-section--alt" id="workflow">
        <div className="landing__container">
          <Reveal>
            <div className="lp-section__head">
              <span className="lp-section__eyebrow">How it works</span>
              <h2 className="lp-section__title">From bedside measurement to explained decision</h2>
              <p className="lp-section__sub">
                Three steps, fully connected — no disconnected spreadsheets, no guesswork.
              </p>
            </div>
          </Reveal>

          <div className="lp-steps">
            <Reveal delay={60}>
              <article className="lp-step">
                <span className="lp-step__number">1</span>
                <h3>Record vitals at the bedside</h3>
                <p>
                  Nurses capture heart rate, blood pressure, oxygen saturation, respiration, and
                  temperature in seconds — from any ward.
                </p>
              </article>
            </Reveal>
            <Reveal delay={160}>
              <article className="lp-step">
                <span className="lp-step__number">2</span>
                <h3>Rules evaluate instantly</h3>
                <p>
                  Your Head of Service&apos;s configured clinical rules classify the patient and
                  check ICU criteria against live specialist and bed availability.
                </p>
              </article>
            </Reveal>
            <Reveal delay={260}>
              <article className="lp-step">
                <span className="lp-step__number">3</span>
                <h3>Recommend, alert &amp; explain</h3>
                <p>
                  An explainable ICU recommendation is stored and escalated — and the assistant
                  communicates it to the people who need to understand it.
                </p>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      {/* --------------------------------- Roles --------------------------------- */}
      <section className="lp-section" id="roles">
        <div className="landing__container lp-assistant">
          <Reveal>
            <div className="lp-hero__visual">
              <div className="lp-hero__card" style={{ animation: 'none' }}>
                <img src={careTeamImage} alt="Doctor and nurse reviewing patient data together on a tablet" />
              </div>
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div className="lp-assistant__copy">
              <span className="lp-section__eyebrow">One hospital, one workspace</span>
              <h2 className="lp-section__title" style={{ textAlign: 'left' }}>
                Built for the whole care team
              </h2>
              <p className="lp-section__sub" style={{ textAlign: 'left' }}>
                Every role gets a focused workspace with exactly the access they need — nothing
                more, nothing less.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 22 }}>
                {ROLES.map((role) => (
                  <span key={role.label} className="lp-hero__eyebrow" style={{ animation: 'none' }}>
                    <role.icon size={14} />
                    {role.label}
                  </span>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------ Testimonials ----------------------------- */}
      <section className="lp-section lp-section--alt" id="testimonials">
        <div className="landing__container">
          <Reveal>
            <div className="lp-section__head">
              <span className="lp-section__eyebrow">Trusted on the ward</span>
              <h2 className="lp-section__title">What the care team says</h2>
            </div>
          </Reveal>

          <div className="lp-testimonials">
            <Reveal delay={60}>
              <article className="lp-testimonial">
                <blockquote>
                  “During night shifts with no intensivist on site, Velora gives us a structured
                  escalation path we can trust — and explain to families.”
                </blockquote>
                <footer>
                  <span className="lp-testimonial__avatar" style={{ background: 'linear-gradient(135deg, #176b87, #2ec4b6)' }}>
                    AM
                  </span>
                  <div>
                    <strong>Dr. A. Manga</strong>
                    <small>Internal Medicine</small>
                  </div>
                </footer>
              </article>
            </Reveal>
            <Reveal delay={160}>
              <article className="lp-testimonial">
                <blockquote>
                  “I record vitals in seconds. When a patient deteriorates, the exact criteria that
                  fired are right there on screen — no guessing, no calling around.”
                </blockquote>
                <footer>
                  <span className="lp-testimonial__avatar" style={{ background: 'linear-gradient(135deg, #b93845, #e85d75)' }}>
                    NB
                  </span>
                  <div>
                    <strong>N. Bello</strong>
                    <small>Charge Nurse, ICU</small>
                  </div>
                </footer>
              </article>
            </Reveal>
            <Reveal delay={260}>
              <article className="lp-testimonial">
                <blockquote>
                  “The assistant explained my mother&apos;s ICU evaluation in words I could actually
                  understand. It made a frightening night feel manageable.”
                </blockquote>
                <footer>
                  <span className="lp-testimonial__avatar" style={{ background: 'linear-gradient(135deg, #a76512, #d99a3d)' }}>
                    CE
                  </span>
                  <div>
                    <strong>C. Efeti</strong>
                    <small>Patient Guard</small>
                  </div>
                </footer>
              </article>
            </Reveal>
          </div>
        </div>
      </section>

      {/* --------------------------------- CTA ----------------------------------- */}
      <section className="lp-cta">
        <div className="landing__container">
          <Reveal>
            <div className="lp-cta__panel">
              <h2>Bring clarity to critical care</h2>
              <p>
                Log in with the account provided by your hospital to open your role-scoped
                workspace — and let every recommendation explain itself.
              </p>
              <div className="lp-cta__actions">
                <Link to={isAuthenticated ? '/workspace' : '/login'} className="lp-button lp-button--light">
                  {isAuthenticated ? 'Open your workspace' : 'Log in now'} <ArrowRight size={16} />
                </Link>
                {!isAuthenticated && (
                  <a href="#platform" className="lp-button lp-button--ghost" style={{ color: '#fff', borderColor: 'rgb(255 255 255 / 40%)', background: 'rgb(255 255 255 / 10%)' }}>
                    Explore features
                  </a>
                )}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* -------------------------------- Footer --------------------------------- */}
      <footer className="lp-footer">
        <div className="landing__container">
          <div className="lp-footer__grid">
            <div className="lp-footer__about">
              <Link to="/" className="landing-brand" style={{ marginBottom: 14 }}>
                <span className="landing-brand__mark">
                  <HeartPulse size={18} />
                </span>
                <span>
                  Velora
                  <small>Hospital workspace</small>
                </span>
              </Link>
              <p>
                A secure, domain-organized hospital management system connecting clinical
                monitoring, ICU decision support, communication, billing, and audit history.
              </p>
            </div>
            <div>
              <h4>Platform</h4>
              <ul>
                <li><a href="#platform">ICU recommendations</a></li>
                <li><a href="#assistant">AI assistant</a></li>
                <li><a href="#workflow">How it works</a></li>
                <li><a href="#roles">Care team roles</a></li>
              </ul>
            </div>
            <div>
              <h4>Workspaces</h4>
              <ul>
                <li><a href="#roles">Head of Service</a></li>
                <li><a href="#roles">Doctors &amp; Nurses</a></li>
                <li><a href="#roles">Patient Guards</a></li>
                <li><a href="#roles">Accounting &amp; Admin</a></li>
              </ul>
            </div>
            <div>
              <h4>Trust</h4>
              <ul>
                <li><a href="#platform"><ShieldCheck size={13} style={{ marginRight: 6, verticalAlign: '-2px' }} />Security model</a></li>
                <li><a href="#platform"><ScrollText size={13} style={{ marginRight: 6, verticalAlign: '-2px' }} />Audit trail</a></li>
                <li><a href="#platform"><Users size={13} style={{ marginRight: 6, verticalAlign: '-2px' }} />Role-scoped access</a></li>
              </ul>
            </div>
          </div>
          <div className="lp-footer__base">
            <span>© 2026 Velora. Built for hospitals that never sleep.</span>
            <span>Clinical decision support — not a replacement for medical judgment.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
