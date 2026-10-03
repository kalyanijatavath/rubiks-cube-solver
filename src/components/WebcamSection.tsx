'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import Webcam from 'react-webcam'

interface WebcamSectionProps {
  onCapture: (imageData: string, shouldFlip: boolean) => void
}

export default function WebcamSection({ onCapture }: WebcamSectionProps) {

  const webcamRef = useRef<Webcam>(null)

  const [isReady, setIsReady] = useState(false)
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment')
  const [isMobile, setIsMobile] = useState(false)

  // Detect mobile device
  useEffect(() => {
    const mobile =
      /Android|iPhone|iPad|iPod|Opera Mini|IEMobile|WPDesktop/i.test(
        navigator.userAgent
      )

    setIsMobile(mobile)
  }, [])

  const handleUserMedia = useCallback(() => {
    setIsReady(true)
  }, [])

  const capture = useCallback(() => {

    if (!webcamRef.current) return

    const imageSrc = webcamRef.current.getScreenshot()

    if (!imageSrc) return

    // Flip logic
    const isMobileRearCamera = isMobile && facingMode === 'environment'

    const shouldFlip = !isMobileRearCamera

    onCapture(imageSrc, shouldFlip)

  }, [onCapture, facingMode, isMobile])

  const switchCamera = () => {
    setFacingMode(prev => prev === 'user' ? 'environment' : 'user')
  }

  return (
    <div className="flex-1 flex flex-col">

      <div className="relative flex-1 bg-black rounded-lg overflow-hidden">

        <Webcam
          ref={webcamRef}
          audio={false}
          screenshotFormat="image/jpeg"
          onUserMedia={handleUserMedia}
          mirrored={!isMobile || facingMode === 'user'}
          className="w-full h-full object-cover"
          videoConstraints={{
            facingMode,
            width: { ideal: 640 },
            height: { ideal: 480 }
          }}
        />

        {/* 3x3 Grid Overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div
            className="border-2 border-white/50"
            style={{ width: '240px', height: '240px' }}
          >
            <div className="grid grid-cols-3 grid-rows-3 h-full">
              {[...Array(9)].map((_, i) => (
                <div key={i} className="border border-white/30" />
              ))}
            </div>
          </div>
        </div>

      </div>

      <div className="mt-4 flex justify-center gap-3">

        <button
          onClick={capture}
          disabled={!isReady}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
        >
          📷 Capture
        </button>

        {isMobile && (
          <button
            onClick={switchCamera}
            className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg"
          >
            🔄 Flip Camera
          </button>
        )}

      </div>

    </div>
  )
}