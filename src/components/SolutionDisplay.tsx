'use client'

import { Move } from '@/lib/cubeSolver'

interface SolutionDisplayProps {
  moves: Move[]
  currentMoveIndex: number
  onMoveClick: (index: number) => void
}

export default function SolutionDisplay({ moves, currentMoveIndex, onMoveClick }: SolutionDisplayProps) {
  if (moves.length === 0) return null
  
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3 text-green-400">🎯 Solution ({moves.length} moves)</h3>
      
      <div className="flex flex-wrap gap-2 mb-4">
        {moves.map((move, index) => (
          <button
            key={index}
            onClick={() => onMoveClick(index)}
            className={`px-3 py-2 rounded-lg font-mono font-bold text-lg transition-all ${
              index < currentMoveIndex 
                ? 'bg-green-600 text-white' 
                : index === currentMoveIndex 
                  ? 'bg-yellow-500 text-black scale-110 ring-2 ring-yellow-300'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {move.notation}
          </button>
        ))}
      </div>
      
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-green-500 transition-all duration-300" style={{ width: `${(currentMoveIndex / moves.length) * 100}%` }} />
        </div>
        <span className="text-sm text-gray-400">{currentMoveIndex}/{moves.length}</span>
      </div>
    </div>
  )
}