'use client'

import { useState, useCallback } from 'react'

// Standard scan order
export const SCAN_ORDER = ['front', 'right', 'back', 'left', 'up', 'down'] as const
export type FaceName = typeof SCAN_ORDER[number]

// Orientation instructions for each face
export const ORIENTATION_GUIDE: Record<FaceName, { text: string; topColor: string; facingColor: string }> = {
  front: { text: 'Green center facing CAMERA, White center on TOP', topColor: 'white', facingColor: 'green' },
  right: { text: 'Red center facing CAMERA, White center on TOP', topColor: 'white', facingColor: 'red' },
  back: { text: 'Blue center facing CAMERA, White center on TOP', topColor: 'white', facingColor: 'blue' },
  left: { text: 'Orange center facing CAMERA, White center on TOP', topColor: 'white', facingColor: 'orange' },
  up: { text: 'White center facing CAMERA, Blue center on TOP', topColor: 'blue', facingColor: 'white' },
  down: { text: 'Yellow center facing CAMERA, Green center on TOP', topColor: 'green', facingColor: 'yellow' }
}

// Color type
export type CubeColor = 'white' | 'yellow' | 'red' | 'orange' | 'blue' | 'green'

// Face state - 9 stickers
export type FaceState = [CubeColor, CubeColor, CubeColor, CubeColor, CubeColor, CubeColor, CubeColor, CubeColor, CubeColor]

// Full cube state
export interface CubeState {
  front: FaceState | null
  right: FaceState | null
  back: FaceState | null
  left: FaceState | null
  up: FaceState | null
  down: FaceState | null
}

// Empty cube state
const EMPTY_CUBE_STATE: CubeState = {
  front: null, right: null, back: null, left: null, up: null, down: null
}

export function useCubeState() {
  const [cubeState, setCubeState] = useState<CubeState>(EMPTY_CUBE_STATE)
  const [currentFaceIndex, setCurrentFaceIndex] = useState(0)
  const [isReviewMode, setIsReviewMode] = useState(false)

  const currentFace: FaceName = SCAN_ORDER[currentFaceIndex]
  const isComplete = currentFaceIndex >= 6
  const progress = Math.min((currentFaceIndex / 6) * 100, 100)
  const orientation = ORIENTATION_GUIDE[currentFace]
  const hasSavedFace = cubeState[currentFace] !== null
  const savedFaceColors = cubeState[currentFace]

  const enterReviewMode = useCallback(() => setIsReviewMode(true), [])
  const exitReviewMode = useCallback(() => setIsReviewMode(false), [])

  const saveFace = useCallback((faceState: FaceState) => {
    setCubeState(prev => ({ ...prev, [currentFace]: faceState }))
    setCurrentFaceIndex(prev => prev + 1)
    setIsReviewMode(false)
  }, [currentFace])

  const nextFace = useCallback(() => {
    setCurrentFaceIndex(prev => prev + 1)
    setIsReviewMode(false)
  }, [])

  const updateCurrentFace = useCallback((faceState: FaceState) => {
    setCubeState(prev => ({ ...prev, [currentFace]: faceState }))
  }, [currentFace])

  const goBack = useCallback(() => {
    if (currentFaceIndex > 0) {
      setCurrentFaceIndex(prev => prev - 1)
      setIsReviewMode(false)
    }
  }, [currentFaceIndex])

  const reset = useCallback(() => {
    setCubeState(EMPTY_CUBE_STATE)
    setCurrentFaceIndex(0)
    setIsReviewMode(false)
  }, [])

  const setFullCubeState = useCallback((state: CubeState) => {
    setCubeState(state)
    setCurrentFaceIndex(6)
    setIsReviewMode(false)
  }, [])

  const clearCurrentFace = () => {
  setCubeState(prev => ({
    ...prev,
    [currentFace]: null
  }))
}

  return {
    cubeState, currentFaceIndex, currentFace, isComplete, isReviewMode, progress,
    orientation, hasSavedFace, savedFaceColors, saveFace, updateCurrentFace,
    goBack, reset, enterReviewMode, exitReviewMode, nextFace, setCubeState: setFullCubeState,clearCurrentFace
  }
}