'use client'

import { useRef, useState, useCallback } from 'react'
import Webcam from 'react-webcam'

const BASE_CONSTRAINTS = {
  width: { ideal: 640 },
  height: { ideal: 480 }
}

export function useWebcam() {

  const webcamRef = useRef<Webcam>(null)

  const [isCameraOn, setIsCameraOn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment')

  const startCamera = useCallback(() => {
    setIsCameraOn(true)
    setError(null)
  }, [])

  const stopCamera = useCallback(() => {
    setIsCameraOn(false)
  }, [])

  const captureImage = useCallback((): string | null => {

    if (!webcamRef.current) {
      setError('Camera not ready')
      return null
    }

    const imageSrc = webcamRef.current.getScreenshot()

    if (!imageSrc) {
      setError('Failed to capture image')
      return null
    }

    return imageSrc

  }, [])

  const handleWebcamError = useCallback((err: string | DOMException) => {

    console.error('Webcam error:', err)

    setError('Could not access camera. Please check permissions.')

    setIsCameraOn(false)

  }, [])

  const switchCamera = useCallback(() => {
    setFacingMode(prev => prev === 'user' ? 'environment' : 'user')
  }, [])

  const videoConstraints = {
    ...BASE_CONSTRAINTS,
    facingMode: { ideal: facingMode }
  }

  return {
    webcamRef,
    isCameraOn,
    error,
    startCamera,
    stopCamera,
    captureImage,
    handleWebcamError,
    switchCamera,
    facingMode,
    videoConstraints
  }
}