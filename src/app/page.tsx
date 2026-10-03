"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import WebcamSection from "@/components/WebcamSection";
import ScanGuide from "@/components/ScanGuide";
import Cube3D from "@/components/Cube3D";
import SolutionDisplay from "@/components/SolutionDisplay";
import {
  useCubeState,
  FaceState,
  CubeColor,
  FaceName,
} from "@/hooks/useCubeState";
import { predictFaceColors, initColorDetection } from "@/lib/cubeUtils";
import {
  solveCube,
  Solution,
  Move,
  validateCubeState,
  applyMoveToCubeState,
} from "@/lib/cubeSolver";

// Color to hex mapping
const COLOR_HEX: Record<CubeColor, string> = {
  white: "#FFFFFF",
  yellow: "#FFD500", // stronger yellow
  red: "#FF0000", // darker red (Rubik's standard)
  orange: "#FF6A00", // deeper orange
  blue: "#0000FF",
  green: "#19C319",
};

// All available colors
const ALL_COLORS: CubeColor[] = [
  "white",
  "yellow",
  "red",
  "orange",
  "blue",
  "green",
];

export default function Home() {
  // Cube state management
  const {
    cubeState,
    currentFaceIndex,
    currentFace,
    isComplete,
    isReviewMode,
    progress,
    orientation,
    hasSavedFace,
    savedFaceColors,
    saveFace,
    updateCurrentFace,
    goBack,
    reset,
    enterReviewMode,
    exitReviewMode,
    nextFace,
    clearCurrentFace,
  } = useCubeState();

  // Model loading state
  const [modelLoaded, setModelLoaded] = useState(false);

  // Temporary colors being edited (for color correction)
  const [editingColors, setEditingColors] = useState<FaceState | null>(null);

  const [selectedColor, setSelectedColor] = useState<CubeColor>("white");
  // Loading state during prediction
  const [isPredicting, setIsPredicting] = useState(false);

  // Prediction error
  const [error, setError] = useState<string | null>(null);

  // Solution state
  const [solution, setSolution] = useState<Solution | null>(null);
  const [isSolving, setIsSolving] = useState(false);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
  const [solveError, setSolveError] = useState<string | null>(null);

  // Move visualization state
  const [visualizedCubeState, setVisualizedCubeState] = useState<Record<
    FaceName,
    FaceState | null
  > | null>(null);
  const [animatingMove, setAnimatingMove] = useState<Move | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Ref for play interval
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Use visualized state if available, otherwise use original cube state
  const displayCubeState = visualizedCubeState || cubeState;

  const colorCounts = useMemo(() => {

  const counts: Record<CubeColor, number> = {
    white: 0,
    yellow: 0,
    red: 0,
    orange: 0,
    blue: 0,
    green: 0
  }

  // Count colors from already scanned faces
  Object.values(cubeState).forEach(face => {

  if (!face) return

  face.forEach((c: CubeColor) => {
    counts[c]++
  })

})

  // If editing current face, subtract previous saved values
  // and add editing values so counts stay correct
  if (editingColors && currentFace) {

    const saved = cubeState[currentFace]

    if (saved) {
      saved.forEach(c => {
        counts[c]--
      })
    }

    editingColors.forEach(c => {
      counts[c]++
    })

  }

  return counts

}, [cubeState, editingColors, currentFace])
  // Load model on mount
  useEffect(() => {
    const loadMLModel = async () => {
      console.log("Loading ML model...");
      const success = await initColorDetection();
      setModelLoaded(success);
      if (success) {
        console.log("ML model loaded successfully!");
      } else {
        console.error("Failed to load ML model");
      }
    };

    loadMLModel();
  }, []);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, []);

  // Handle when user captures a face
  const handleCapture = async (imageData: string, shouldFlip: boolean) => {
    console.log("Face captured:", currentFace);
    setError(null);

    if (!modelLoaded) {
      setError("Model not loaded yet. Please wait...");
      return;
    }

    setIsPredicting(true);

    try {
      // Predict colors using ML model
      const predictedColors = await predictFaceColors(imageData, shouldFlip);

      const faceState = [...predictedColors] as FaceState;

      // Fix center color based on face
      const FACE_CENTER_COLOR: Record<FaceName, CubeColor> = {
        front: "green",
        back: "blue",
        right: "red",
        left: "orange",
        up: "white",
        down: "yellow",
      };

      faceState[4] = FACE_CENTER_COLOR[currentFace];

      console.log("Predicted colors:", predictedColors);

      // Set as editing colors for review
      setEditingColors(faceState);
      setError(null);
    } catch (err) {
      console.error("Prediction error:", err);
      setError("Failed to predict colors. Please try again.");
    } finally {
      setIsPredicting(false);
    }
  };

  // Handle going back to previous face
  const handleBack = () => {
    setEditingColors(null);
    setError(null);
    goBack();
  };

  // Confirm colors and save
  const handleConfirm = () => {
    if (editingColors) {
      saveFace(editingColors);
      setEditingColors(null);
      setError(null);
    }
  };

  // Start editing saved face
  const handleEditSaved = () => {
    if (savedFaceColors) {
      setEditingColors(savedFaceColors);
      enterReviewMode();
    }
  };

  // Update a single sticker color
  const handleColorChange = (index: number, color: CubeColor) => {
    if (editingColors) {
      const newColors = [...editingColors] as FaceState;
      newColors[index] = color;
      setEditingColors(newColors);
    }
  };

  // Continue to next face with saved colors
  const skipToNext = () => {
    nextFace();
  };

  // Solve the cube
  const handleSolve = async () => {
    setIsSolving(true);
    setSolveError(null);
    setSolution(null);

    try {
      // Validate cube state
      const validation = validateCubeState(cubeState);
      if (!validation.valid) {
        setSolveError(validation.error || "Invalid cube state");
        setIsSolving(false);
        return;
      }

      // Solve the cube (async)
      const result = await solveCube(cubeState);

      if (result) {
        setSolution(result);
        setCurrentMoveIndex(0);
        setVisualizedCubeState(cubeState); // Initialize visualization state
        console.log("Solution found:", result.notation);
      } else {
        setSolveError("Could not find a solution");
      }
    } catch (err) {
      console.error("Solver error:", err);
      setSolveError("Failed to solve cube");
    } finally {
      setIsSolving(false);
    }
  };

  // Handle move click in solution - jump to that move
  const handleMoveClick = useCallback(
    (index: number) => {
      if (!solution) return;

      // Stop any playing animation
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
        setIsPlaying(false);
      }

      // Calculate state up to the clicked move
      let state = cubeState;
      for (let i = 0; i < index; i++) {
        state = applyMoveToCubeState(state, solution.moves[i]);
      }

      setVisualizedCubeState(state);
      setCurrentMoveIndex(index);
    },
    [solution, cubeState],
  );

  // Initialize visualization with original cube state
  const initVisualization = useCallback(() => {
    setVisualizedCubeState(cubeState);
    setCurrentMoveIndex(0);
  }, [cubeState]);

  // Apply a single move with animation
  const applyMove = useCallback((move: Move, onComplete?: () => void) => {
    setAnimatingMove(move);

    // After animation completes, update the cube state
    setTimeout(() => {
      setVisualizedCubeState((prev) => {
        if (!prev) return prev;
        return applyMoveToCubeState(prev, move);
      });
      setAnimatingMove(null);
      onComplete?.();
    }, 1000); // Match animation duration
  }, []);

  // Next move
  const nextMove = useCallback(() => {
    if (!solution || currentMoveIndex >= solution.moves.length) return;

    const move = solution.moves[currentMoveIndex];
    applyMove(move);
    setCurrentMoveIndex((prev) => prev + 1);
  }, [solution, currentMoveIndex, applyMove]);

  // Previous move

  function getInverseMove(move: Move): Move {

  if (move.direction === "cw") {
    return { ...move, direction: "ccw", notation: move.face + "'" }
  }

  if (move.direction === "ccw") {
    return { ...move, direction: "cw", notation: move.face }
  }

  return move // double move stays same
}
  const prevMove = useCallback(() => {

  if (!solution || currentMoveIndex <= 0) return

  if (playIntervalRef.current) {
    clearInterval(playIntervalRef.current)
    playIntervalRef.current = null
    setIsPlaying(false)
  }

  const move = solution.moves[currentMoveIndex - 1]

  const inverseMove = getInverseMove(move)

  applyMove(inverseMove)

  setCurrentMoveIndex(prev => prev - 1)

}, [solution, currentMoveIndex, applyMove])

  // Play all moves automatically
  const playAll = useCallback(() => {
    if (!solution) return;

    // Stop any existing interval
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
    }

    // Reset to initial state
    initVisualization();
    setIsPlaying(true);

    let index = 0;
    playIntervalRef.current = setInterval(() => {
      if (index >= solution.moves.length) {
        if (playIntervalRef.current) {
          clearInterval(playIntervalRef.current);
          playIntervalRef.current = null;
        }
        setIsPlaying(false);
        return;
      }

      const move = solution.moves[index];

      applyMove(move);
      setCurrentMoveIndex(index + 1);
      index++;
    }, 1500); // 400ms between moves for smoother visualization
  }, [solution, initVisualization]);

  // Stop playing
  const stopPlaying = useCallback(() => {
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  // Reset visualization to original state
  const resetVisualization = useCallback(() => {
    // Stop any playing animation
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
    setVisualizedCubeState(cubeState);
    setCurrentMoveIndex(0);
    setIsPlaying(false);
  }, [cubeState]);

  // Reset everything including solution
  const handleFullReset = useCallback(() => {
    // Stop any playing animation
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
    reset();
    setSolution(null);
    setCurrentMoveIndex(0);
    setSolveError(null);
    setVisualizedCubeState(null);
    setAnimatingMove(null);
    setIsPlaying(false);
  }, [reset]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 px-6 py-4 border-b border-gray-700">
        <h1 className="text-2xl font-bold text-center">
          🧊 Rubik's Cube Solver
        </h1>
        {/* Model status */}
        <p className="text-xs text-center mt-1">
          {modelLoaded ? (
            <span className="text-green-400">✓ AI Model Ready</span>
          ) : (
            <span className="text-yellow-400">⏳ Loading AI Model...</span>
          )}
        </p>
        {/* Progress bar */}
        <div className="mt-2 max-w-md mx-auto">
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </header>

      {/* Main Content - Two Columns */}
      <main className="flex flex-col lg:flex-row gap-4 p-4 h-[calc(100vh-120px)]">
        {/* LEFT SECTION - Webcam */}
        <section className="flex-1 bg-gray-800 rounded-lg p-4 flex flex-col">
          {/* Show Scan Guide if not complete */}
          {!isComplete && (
            <ScanGuide
              currentFace={currentFace}
              currentFaceIndex={currentFaceIndex}
              orientation={orientation}
            />
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-2 rounded-lg mb-4 text-sm">
              {error}
            </div>
          )}

          {/* Main Content Area */}
          {!isComplete ? (
            <>
              {/* If face already saved and not editing - show options */}
              {hasSavedFace && !editingColors ? (
                <div className="flex-1 bg-gray-900 rounded-lg p-4 flex flex-col items-center justify-center">
                  <p className="text-lg mb-4">
                    This face is already scanned ✅
                  </p>
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    {savedFaceColors?.map((color, index) => (
                      <div
                        key={index}
                        className="w-12 h-12 rounded border-2 border-gray-600"
                        style={{ backgroundColor: COLOR_HEX[color] }}
                      />
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={skipToNext}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
                    >
                      Continue →
                    </button>
                    <button
                      onClick={handleEditSaved}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                    >
                      Edit Colors
                    </button>
                  </div>
                </div>
              ) : editingColors ? (
                /* Color Correction Mode */
                <div className="flex-1 bg-gray-900 rounded-lg p-4 flex flex-col">
                  <h3 className="text-lg font-semibold mb-2 text-yellow-400">
                    🎨 Correct Colors (if needed)
                  </h3>
                  <p className="text-sm text-gray-400 mb-4">
                    Click a sticker to change its color
                  </p>

                  {/* 3x3 Color Grid */}
                  <div className="grid grid-cols-3 gap-2 mb-4 justify-center max-w-[200px] mx-auto">
                    {editingColors.map((color, index) => (
                      <div key={index} className="relative group">
                        <button
                          className={`w-16 h-16 rounded-lg border-2
${index === 4 ? "border-yellow-300 cursor-not-allowed" : "border-gray-600 hover:border-white"}`}
                          style={{ backgroundColor: COLOR_HEX[color] }}
                          onClick={() => {
                            if (index !== 4)
                              handleColorChange(index, selectedColor);
                          }}
                        />
                        <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] text-gray-500">
                          {index + 1}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap justify-center gap-4 mb-4">
                    {ALL_COLORS.map((c) => {
                      const count = colorCounts[c];
                      const isComplete = count === 9;
                      const isDisabled = count >= 9;

                      return (
                        <button
                          key={c}
                          disabled={isDisabled}
                          onClick={() => setSelectedColor(c)}
                          className={`flex flex-col items-center transition
        ${selectedColor === c ? "scale-110" : ""}
        ${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                          <div
                            className={`w-10 h-10 rounded-full border-4
          ${selectedColor === c ? "border-white" : "border-gray-700"}`}
                            style={{ backgroundColor: COLOR_HEX[c] }}
                          />

                          <span
                            className={`text-xs mt-1
          ${isComplete ? "text-green-400" : "text-red-400"}`}
                          >
                            {count}/9
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  {Object.values(colorCounts).some((c) => c !== 9) && (
                    <p className="text-red-400 text-sm text-center mt-2">
                      ⚠ Each color must appear exactly 9 times
                    </p>
                  )}
                  {/* Action Buttons */}
                  <div className="flex gap-2 justify-center">
                    <button
                      onClick={handleConfirm}
                      disabled={Object.values(colorCounts).some((c) => c > 9)}
                      className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors font-medium"
                    >
                      ✓ Confirm & Continue
                    </button>
                    <button
                      onClick={() => {
  clearCurrentFace()
  setEditingColors(null)
}}
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg transition-colors font-medium"
                    >
                      🔄 Rescan Face
                    </button>
                  </div>
                </div>
              ) : (
                /* Webcam Mode */
                <>
                  {isPredicting ? (
                    <div className="flex-1 bg-gray-900 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <div className="animate-spin text-4xl mb-4">⏳</div>
                        <p className="text-lg">Detecting colors...</p>
                      </div>
                    </div>
                  ) : (
                    <WebcamSection onCapture={handleCapture} />
                  )}
                </>
              )}
            </>
          ) : (
            /* All faces scanned */
            <div className="flex-1 flex flex-col">
              <div className="text-center py-4">
                <p className="text-4xl mb-2">✅</p>
                <h2 className="text-xl font-bold text-green-400 mb-2">
                  Scanning Complete!
                </h2>
                <p className="text-gray-400 text-sm mb-4">
                  All 6 faces have been scanned
                </p>
              </div>

              {/* Solve button */}
              {!solution && (
                <div className="text-center mb-4">
                  {solveError && (
                    <p className="text-red-400 text-sm mb-2">{solveError}</p>
                  )}
                  <button
                    onClick={handleSolve}
                    disabled={isSolving}
                    className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg transition-colors font-medium disabled:opacity-50"
                  >
                    {isSolving ? "🔄 Solving..." : "🎯 Solve Cube"}
                  </button>
                </div>
              )}

              {/* Solution display */}
              {solution && (
                <div className="space-y-3">
                  <SolutionDisplay
                    moves={solution.moves}
                    currentMoveIndex={currentMoveIndex}
                    onMoveClick={handleMoveClick}
                  />

                  {/* Play controls */}
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    <button
                      onClick={prevMove}
                      disabled={currentMoveIndex <= 0}
                      className="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      ⏮ Prev
                    </button>

                    {isPlaying ? (
                      <button
                        onClick={stopPlaying}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors font-medium"
                      >
                        ⏸ Pause
                      </button>
                    ) : (
                      <button
                        onClick={playAll}
                        disabled={currentMoveIndex >= solution.moves.length}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium disabled:opacity-50"
                      >
                        ▶ Play
                      </button>
                    )}

                    <button
                      onClick={nextMove}
                      disabled={currentMoveIndex >= solution.moves.length}
                      className="px-3 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next ⏭
                    </button>

                    <button
                      onClick={resetVisualization}
                      className="px-3 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg transition-colors"
                    >
                      🔄 Reset
                    </button>
                  </div>
                </div>
              )}

              {/* Solution info */}
              {solution && solution.moves.length > 0 && (
                <div className="mt-4 p-3 bg-gray-800 rounded-lg text-center">
                  <p className="text-sm text-gray-400">
                    Solution:{" "}
                    <span className="text-white font-mono">
                      {solution.notation}
                    </span>
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {solution.moveCount} moves • Click a move to jump to that
                    position
                  </p>
                </div>
              )}

              {/* Already solved message */}
              {solution && solution.moves.length === 0 && (
                <div className="mt-4 p-3 bg-green-800/50 rounded-lg text-center">
                  <p className="text-green-400">
                    🎉 Your cube is already solved!
                  </p>
                </div>
              )}

              {/* Rescan button */}
              <div className="text-center mt-auto pt-4">
                <button
                  onClick={handleFullReset}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors text-sm"
                >
                  🔄 Rescan All
                </button>
              </div>
            </div>
          )}

          {/* Back Button */}
          {currentFaceIndex > 0 && !isComplete && (
            <button
              onClick={handleBack}
              className="mt-2 px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-lg transition-colors text-sm"
            >
              ← Back to Previous Face
            </button>
          )}
        </section>

        {/* RIGHT SECTION - 3D Cube */}
        <section className="flex-1 bg-gray-800 rounded-lg p-4 flex flex-col">
          <h2 className="text-lg font-semibold mb-4 text-green-400">
            🎲 3D Cube View
          </h2>

          {/* 3D Cube Visualization */}
          <div className="flex-1 bg-gray-900 rounded-lg overflow-hidden min-h-[300px]">
            <Cube3D
              cubeState={displayCubeState}
              currentFace={currentFace}
              animatingMove={animatingMove}
            />
          </div>

          <p className="text-xs text-center text-gray-500 mt-2">
            Drag to rotate • Scroll to zoom
          </p>

          {/* Show scanned faces summary */}
          <div className="mt-4">
            <p className="text-sm text-gray-400 mb-2">Scanned Faces:</p>
            <div className="grid grid-cols-6 gap-1">
              {Object.entries(cubeState).map(([face, colors]) => (
                <div key={face} className="text-center">
                  <div
                    className={`w-8 h-8 mx-auto rounded ${
                      colors ? "bg-green-600" : "bg-gray-600"
                    }`}
                  />
                  <span className="text-[10px] text-gray-500">
                    {face[0].toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
