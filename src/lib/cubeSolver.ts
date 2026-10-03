  /**
   * Rubik's Cube Solver
   * Uses rubik-cube-solver library for Kociemba algorithm solutions
   */

  import { CubeColor, FaceName, FaceState } from '@/hooks/useCubeState'

  // Face type
  type Face = 'U' | 'D' | 'F' | 'B' | 'L' | 'R'

  // Move definition
  export interface Move {
    face: Face
    direction: 'cw' | 'ccw' | 'double'
    notation: string
  }

  // Solution result
  export interface Solution {
    moves: Move[]
    notation: string
    moveCount: number
  }

  // Color to face mapping (based on standard cube orientation)
  const COLOR_TO_FACE: Record<CubeColor, Face> = {
    white: 'U',    // Up
    yellow: 'D',   // Down
    green: 'F',    // Front
    blue: 'B',     // Back
    orange: 'L',   // Left
    red: 'R'       // Right
  }

  /**
   * Validate cube state
   */
  export function validateCubeState(cubeState: Record<FaceName, FaceState | null>): { valid: boolean; error?: string } {
    for (const [face, colors] of Object.entries(cubeState)) {
      if (!colors) {
        return { valid: false, error: `${face} face not scanned` }
      }
    }

    const counts: Record<CubeColor, number> = { 
      white: 0, yellow: 0, red: 0, orange: 0, blue: 0, green: 0 
    }
    
    for (const colors of Object.values(cubeState)) {
      for (const color of colors!) {
        counts[color]++
      }
    }

    for (const [color, count] of Object.entries(counts)) {
      if (count !== 9) {
        return { valid: false, error: `${color} appears ${count} times (should be 9)` }
      }
    }

    return { valid: true }
  }

  /**
   * Convert cube state to Kociemba notation string
   * Order: U1-U9, R1-R9, F1-F9, D1-D9, L1-L9, B1-B9
   */
  function cubeToKociembaString(cubeState: Record<FaceName, FaceState | null>): string | null {
    for (const colors of Object.values(cubeState)) {
      if (!colors) return null
    }

    // Kociemba order: U, R, F, D, L, B
    const order: FaceName[] = ['up', 'right', 'front', 'down', 'left', 'back']
    
    return order.map(face => {
      const colors = cubeState[face]!
      return colors.map(c => COLOR_TO_FACE[c]).join('')
    }).join('')
  }

  /**
   * Check if cube is already solved
   */
  function isSolved(cubeState: Record<FaceName, FaceState | null>): boolean {
    const stateString = cubeToKociembaString(cubeState)
    if (!stateString) return false
    
    // Check each face has uniform color
    for (let i = 0; i < 6; i++) {
      const face = stateString.slice(i * 9, (i + 1) * 9)
      const center = face[4]
      if (!face.split('').every(c => c === center)) {
        return false
      }
    }
    
    return true
  }

  /**
   * Parse solution string to Move array
   */
  function parseSolution(solutionStr: string): Move[] {

  const moves: Move[] = []
  const tokens = solutionStr.trim().split(/\s+/)

  const validFaces: Face[] = ['U','D','F','B','L','R']

  for (const token of tokens) {

    if (!token) continue

    const faceChar = token[0].toUpperCase()

    if (!validFaces.includes(faceChar as Face)) continue

    const face = faceChar as Face

    let direction: 'cw' | 'ccw' | 'double' = 'cw'
    let notation = face

    if (token.endsWith("2")) {
      direction = 'double'
      notation = face + "2"
    }

    else if (token.endsWith("'")) {
      direction = 'ccw'
      notation = face + "'"
    }

    moves.push({
      face,
      direction,
      notation
    })
  }

  return moves
}

  // Store for the solver class
  let CubeClass: any = null

  /**
   * Initialize the solver (call this on client side)
   */
  async function initSolver(): Promise<boolean> {
    if (CubeClass) return true
    
    try {
      // Dynamic import for client-side only
      const solverModule = await import('rubik-cube-solver')
      CubeClass = solverModule.Cube
      // Initialize the solver tables
      CubeClass.initSolver()
      console.log('rubik-cube-solver initialized successfully')
      return true
    } catch (error) {
      console.error('Failed to load rubik-cube-solver:', error)
      return false
    }
  }

  /**
   * Solve the cube using rubik-cube-solver library (Kociemba algorithm)
   */
  export async function solveCube(cubeState: Record<FaceName, FaceState | null>): Promise<Solution | null> {
    // Validate
    const validation = validateCubeState(cubeState)
    if (!validation.valid) {
      console.error('Invalid cube state:', validation.error)
      return null
    }

    // Print cube state for debugging
    console.log('=== CUBE STATE ===')
    console.log('Raw state:', cubeState)
    
    const faceOrder: FaceName[] = ['up', 'right', 'front', 'down', 'left', 'back']
    console.log('\nFace by face (3x3 grid):')
    for (const face of faceOrder) {
      const colors = cubeState[face]!
      console.log(`\n${face.toUpperCase()} face:`)
      console.log(`${colors[0]} ${colors[1]} ${colors[2]}`)
      console.log(`${colors[3]} ${colors[4]} ${colors[5]}`)
      console.log(`${colors[6]} ${colors[7]} ${colors[8]}`)
    }

    // Check if already solved
    if (isSolved(cubeState)) {
      console.log('\n✅ Cube is already solved!')
      return {
        moves: [],
        notation: 'Already solved!',
        moveCount: 0
      }
    }

    // Convert to Kociemba string
    const stateString = cubeToKociembaString(cubeState)
    if (!stateString) {
      console.error('Failed to convert cube state')
      return null
    }

    console.log('\nKociemba notation (54 chars):')
    console.log('U:', stateString.slice(0, 9))
    console.log('R:', stateString.slice(9, 18))
    console.log('F:', stateString.slice(18, 27))
    console.log('D:', stateString.slice(27, 36))
    console.log('L:', stateString.slice(36, 45))
    console.log('B:', stateString.slice(45, 54))
    console.log('Full string:', stateString)

    try {
      // Initialize solver
      const initialized = await initSolver()
      
      if (initialized && CubeClass) {
        console.log('\n🔍 Running rubik-cube-solver (Kociemba)...')
        
        // Create cube from string and solve
        const cube = CubeClass.fromString(stateString)
        const solutionStr = cube.solve()
        
        console.log('Raw solution:', solutionStr)
        
        const moves = parseSolution(solutionStr)
        
        console.log(`\n✅ Solution found: ${moves.length} moves`)
        
        return {
          moves,
          notation: moves.map(m => m.notation).join(' '),
          moveCount: moves.length
        }
      }
      
      // Fallback if solver not available
      console.log('\n⚠️ Solver not available')
      return null
    } catch (error) {
      console.error('Solver error:', error)
      return null
    }
  }

  /**
   * Parse move notation string to Move array
   */
  export function parseMoveNotation(notation: string): Move[] {
    return parseSolution(notation)
  }

  /**
   * Apply a move to cube state and return new state
   */
  export function applyMoveToCubeState(
    cubeState: Record<FaceName, FaceState | null>,
    move: Move
  ): Record<FaceName, FaceState | null> {
    if (!cubeState.up || !cubeState.down || !cubeState.front || 
        !cubeState.back || !cubeState.left || !cubeState.right) {
      return cubeState
    }

    // Clone the state deeply
    const newState: Record<FaceName, FaceState> = {
      up: [...cubeState.up] as FaceState,
      down: [...cubeState.down] as FaceState,
      front: [...cubeState.front] as FaceState,
      back: [...cubeState.back] as FaceState,
      left: [...cubeState.left] as FaceState,
      right: [...cubeState.right] as FaceState
    }

    // Rotate the face itself
    const faceMap: Record<Face, FaceName> = {
      U: 'up', D: 'down', F: 'front', B: 'back', L: 'left', R: 'right'
    }
    
    const faceName = faceMap[move.face]
    newState[faceName] = rotateFace(newState[faceName], move.direction)

    // Rotate adjacent edges
    const times =
    move.direction === 'double' ? 2 :
    move.direction === 'ccw' ? 3 : 1

  for (let i = 0; i < times; i++) {

    const m = MOVE_TABLE[move.face]

    cycleEdges(
      newState,
      m.faces,
      m.idx
    )

  }

    return newState
  }

  /**
   * Rotate a face's stickers (clockwise when looking at the face)
   */
  function rotateFace(face: FaceState, direction: 'cw' | 'ccw' | 'double'): FaceState {
    const f = face
    
    if (direction === 'cw') {
      // CW rotation: corners rotate 90°, edges rotate 90°
      // 0 1 2    6 3 0
      // 3 4 5 -> 7 4 1
      // 6 7 8    8 5 2
      return [f[6], f[3], f[0], f[7], f[4], f[1], f[8], f[5], f[2]] as FaceState
    } else if (direction === 'ccw') {
      // CCW rotation
      // 0 1 2    2 5 8
      // 3 4 5 -> 1 4 7
      // 6 7 8    0 3 6
      return [f[2], f[5], f[8], f[1], f[4], f[7], f[0], f[3], f[6]] as FaceState
    } else {
      // double (180°)
      return [f[8], f[7], f[6], f[5], f[4], f[3], f[2], f[1], f[0]] as FaceState
    }
  }

  function cycleEdges(
    state: Record<FaceName, FaceState>,
    faces: FaceName[],
    indices: number[][]
  ) {
    const temp = indices[3].map((_, j) => state[faces[3]][indices[3][j]])

    for (let i = 3; i > 0; i--) {
      indices[i].forEach((idx, j) => {
        state[faces[i]][idx] = state[faces[i - 1]][indices[i - 1][j]]
      })
    }

    indices[0].forEach((idx, j) => {
      state[faces[0]][idx] = temp[j]
    })
  }

  const MOVE_TABLE: Record<
  Face,
  {
    faces: FaceName[]
    idx: number[][]
  }
> = {

  U: {
    faces: ['front','left','back','right'],
    idx: [[0,1,2],[0,1,2],[0,1,2],[0,1,2]]
  },

  D: {
    faces: ['front','right','back','left'],
    idx: [[6,7,8],[6,7,8],[6,7,8],[6,7,8]]
  },

  F: {
    faces: ['up','right','down','left'],
    idx: [[6,7,8],[0,3,6],[2,1,0],[8,5,2]]
  },

  B: {
    faces: ['up','left','down','right'],
    idx: [[2,1,0],[0,3,6],[6,7,8],[8,5,2]]
  },

  L: {
    faces: ['up','front','down','back'],
    idx: [[0,3,6],[0,3,6],[0,3,6],[8,5,2]]
  },

  R: {
    faces: ['up','back','down','front'],
    idx: [[8,5,2],[0,3,6],[8,5,2],[8,5,2]]
  }

}

