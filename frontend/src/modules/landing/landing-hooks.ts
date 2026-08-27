import { useEffect, useRef, useState } from 'react'


/**
 * Feature-detecting helpers (jsdom and older browsers do not implement
 * matchMedia for these queries).
 */
function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function hasFinePointer(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches
}

/**
 * Scroll-reveal: adds a class when the element scrolls into view so CSS can
 * animate it in. Falls back to "visible" when prefers-reduced-motion is set.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: { threshold?: number }) {
  const ref = useRef<T | null>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return
    }

    const mediaQuery = prefersReducedMotion()
    if (mediaQuery) {
      setVisible(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true)
            observer.disconnect()
          }
        }
      },
      { threshold: options?.threshold ?? 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [options?.threshold])

  return { ref, visible }
}

/**
 * 3D tilt: rotates the card toward the pointer using CSS perspective.
 * Disabled automatically on touch devices and reduced-motion preferences.
 */
export function useTilt<T extends HTMLElement = HTMLDivElement>(maxDeg = 8) {
  const ref = useRef<T | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (prefersReducedMotion()) return
    if (!hasFinePointer()) return

    let frame = 0

    const onMove = (event: PointerEvent) => {
      const rect = node.getBoundingClientRect()
      const x = (event.clientX - rect.left) / rect.width - 0.5
      const y = (event.clientY - rect.top) / rect.height - 0.5
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        node.style.transform = `perspective(1100px) rotateX(${(-y * maxDeg).toFixed(2)}deg) rotateY(${(x * maxDeg).toFixed(2)}deg)`
        node.style.setProperty('--tilt-x', x.toFixed(3))
        node.style.setProperty('--tilt-y', y.toFixed(3))
      })
    }

    const onLeave = () => {
      cancelAnimationFrame(frame)
      node.style.transform = 'perspective(1100px) rotateX(0deg) rotateY(0deg)'
    }

    node.addEventListener('pointermove', onMove)
    node.addEventListener('pointerleave', onLeave)
    return () => {
      cancelAnimationFrame(frame)
      node.removeEventListener('pointermove', onMove)
      node.removeEventListener('pointerleave', onLeave)
    }
  }, [maxDeg])

  return ref
}

/**
 * Animated counter that runs once the element becomes visible.
 */
export function useCountUp(target: number, durationMs = 1400) {
  const { ref, visible } = useReveal<HTMLSpanElement>({ threshold: 0.4 })
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!visible) return
    if (typeof window !== 'undefined' && prefersReducedMotion()) {
      setValue(target)
      return
    }
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(target * eased))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [visible, target, durationMs])

  return { ref, value }
}

/**
 * Subtle scroll parallax (translateY) for decorative layers.
 */
export function useParallax<T extends HTMLElement = HTMLDivElement>(strength = 24) {
  const ref = useRef<T | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (typeof window === 'undefined' || prefersReducedMotion()) return

    let frame = 0
    const onScroll = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const offset = Math.min(window.innerHeight, window.scrollY)
        node.style.transform = `translate3d(0, ${(offset / window.innerHeight) * strength}px, 0)`
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
    }
  }, [strength])

  return ref
}
