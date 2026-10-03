'use client'

import { FaceName } from '@/hooks/useCubeState'

interface ScanGuideProps {
  currentFace: FaceName
  currentFaceIndex: number
  orientation: { text: string; topColor: string; facingColor: string }
}

const FACE_DISPLAY: Record<FaceName, string> = {
  front: 'Front (Green)', right: 'Right (Red)', back: 'Back (Blue)',
  left: 'Left (Orange)', up: 'Up (White)', down: 'Down (Yellow)'
}

export default function ScanGuide({ currentFace, currentFaceIndex, orientation }: ScanGuideProps) {
  return (
    <div className="bg-gray-900 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-blue-400">Step {currentFaceIndex + 1} of 6</h3>
        <span className="text-sm text-gray-400">{FACE_DISPLAY[currentFace]}</span>
      </div>
      
      <div className="bg-gray-800 rounded-lg p-3">
        <p className="text-white font-medium mb-2">📍 Orientation:</p>
        <p className="text-yellow-400 text-sm">{orientation.text}</p>
        
        <div className="flex gap-4 mt-3 text-xs">
          <div className="flex items-center gap-1">
            <span className="text-gray-400">Top:</span>
            <span className="capitalize font-medium">{orientation.topColor}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-400">Facing:</span>
            <span className="capitalize font-medium">{orientation.facingColor}</span>
          </div>
        </div>
      </div>
    </div>
  )
}