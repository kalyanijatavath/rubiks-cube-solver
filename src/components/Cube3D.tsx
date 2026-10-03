'use client'

import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, RoundedBox } from '@react-three/drei'
import * as THREE from 'three'
import { CubeColor, FaceName } from '@/hooks/useCubeState'
import { Move } from '@/lib/cubeSolver'

const COLOR_HEX: Record<CubeColor, string> = {
  white: '#FFFFFF',
  yellow: '#FFEB3B',
  red: '#F44336',
  orange: '#FF9800',
  blue: '#2196F3',
  green: '#4CAF50'
}

const DEFAULT_COLORS: Record<FaceName, CubeColor> = {
  front: 'green',
  right: 'red',
  back: 'blue',
  left: 'orange',
  up: 'white',
  down: 'yellow'
}

interface Cube3DProps {
  cubeState: Record<FaceName, CubeColor[] | null>
  currentFace?: FaceName | null
  animatingMove?: Move | null
}

function Sticker({
  position,
  color,
  rotation
}:{
  position:[number,number,number]
  color:CubeColor
  rotation:[number,number,number]
}){
  return(
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={[0.85,0.85]}/>
      <meshStandardMaterial color={COLOR_HEX[color]} />
    </mesh>
  )
}

function Cubie({
  position,
  colors
}:{
  position:[number,number,number]
  colors:any
}){
  return(
    <group position={position}>
      <RoundedBox args={[0.95,0.95,0.95]} radius={0.05}>
        <meshStandardMaterial color="#1a1a1a"/>
      </RoundedBox>

      {colors.front && <Sticker position={[0,0,0.5]} color={colors.front} rotation={[0,0,0]}/>}
      {colors.back && <Sticker position={[0,0,-0.5]} color={colors.back} rotation={[0,Math.PI,0]}/>}
      {colors.left && <Sticker position={[-0.5,0,0]} color={colors.left} rotation={[0,-Math.PI/2,0]}/>}
      {colors.right && <Sticker position={[0.5,0,0]} color={colors.right} rotation={[0,Math.PI/2,0]}/>}
      {colors.up && <Sticker position={[0,0.5,0]} color={colors.up} rotation={[-Math.PI/2,0,0]}/>}
      {colors.down && <Sticker position={[0,-0.5,0]} color={colors.down} rotation={[Math.PI/2,0,0]}/>}
    </group>
  )
}

const getStickerColor=(cubeState:any,face:FaceName,index:number)=>{
  if(cubeState[face] && cubeState[face][index]) return cubeState[face][index]
  return DEFAULT_COLORS[face]
}

function RubiksCube({ cubeState, animatingMove }: Cube3DProps) {

  const layerRef = useRef<THREE.Group>(null)
  const rotationRef = useRef(0)

  useFrame(() => {

  if (!animatingMove || !layerRef.current) return

  const speed = 0.08
  const target =
    animatingMove.direction === 'double'
      ? Math.PI
      : Math.PI / 2

  rotationRef.current += speed

  if (rotationRef.current >= target) {
    rotationRef.current = target
  }

  let axis: 'x' | 'y' | 'z' = 'y'
  let sign = 1

  switch (animatingMove.face) {

    case 'U':
      axis = 'y'
      sign = -1
      break

    case 'D':
      axis = 'y'
      sign = 1
      break

    case 'R':
      axis = 'x'
      sign = -1
      break

    case 'L':
      axis = 'x'
      sign = 1
      break

    case 'F':
      axis = 'z'
      sign = -1
      break

    case 'B':
      axis = 'z'
      sign = 1
      break
  }

  if (animatingMove.direction === 'ccw') {
    sign *= -1
  }

  layerRef.current.rotation[axis] = rotationRef.current * sign

})

  useEffect(() => {
    if (!animatingMove) {
      rotationRef.current = 0
      if (layerRef.current) {
        layerRef.current.rotation.set(0,0,0)
      }
    }
  }, [animatingMove])

  const cubies = useMemo(() => {

    const staticCubies = []
    const movingCubies = []

    for (let x=-1;x<=1;x++){
      for (let y=-1;y<=1;y++){
        for (let z=-1;z<=1;z++){

          if(x===0 && y===0 && z===0) continue

          const colors:any = {}

          if(z===1){
            const col=x+1
            const row=1-y
            colors.front=getStickerColor(cubeState,'front',row*3+col)
          }

          if(z===-1){
            const col=1-x
            const row=1-y
            colors.back=getStickerColor(cubeState,'back',row*3+col)
          }

          if(x===1){
            const col=1-z
            const row=1-y
            colors.right=getStickerColor(cubeState,'right',row*3+col)
          }

          if(x===-1){
            const col=z+1
            const row=1-y
            colors.left=getStickerColor(cubeState,'left',row*3+col)
          }

          if(y===1){
            const col=x+1
            const row=z+1
            colors.up=getStickerColor(cubeState,'up',row*3+col)
          }

          if(y===-1){
            const col=x+1
            const row=1-z
            colors.down=getStickerColor(cubeState,'down',row*3+col)
          }

          const cubie = (
            <Cubie
              key={`${x}-${y}-${z}`}
              position={[x,y,z]}
              colors={colors}
            />
          )

          const isMoving =
            animatingMove &&
            (
              (animatingMove.face === 'U' && y === 1) ||
              (animatingMove.face === 'D' && y === -1) ||
              (animatingMove.face === 'L' && x === -1) ||
              (animatingMove.face === 'R' && x === 1) ||
              (animatingMove.face === 'F' && z === 1) ||
              (animatingMove.face === 'B' && z === -1)
            )

          if(isMoving){
            movingCubies.push(cubie)
          }else{
            staticCubies.push(cubie)
          }

        }
      }
    }

    return { staticCubies, movingCubies }

  }, [cubeState, animatingMove])

  return (
    <group>

      {cubies.staticCubies}

      <group ref={layerRef}>
        {cubies.movingCubies}
      </group>

    </group>
  )
}

function CameraController(){
  const {camera}=useThree()

  useEffect(()=>{
    camera.position.set(4,3,4)
    camera.lookAt(0,0,0)
  },[camera])

  return null
}

export default function Cube3D({cubeState,animatingMove}:Cube3DProps){

  return(
    <div className="w-full h-full min-h-[300px]">

      <Canvas camera={{position:[4,3,4],fov:50}}>

        <ambientLight intensity={0.6}/>
        <directionalLight position={[5,5,5]} intensity={0.8}/>

        <RubiksCube
          cubeState={cubeState}
          animatingMove={animatingMove}
        />

        <CameraController/>

        <OrbitControls
          enablePan={false}
          minDistance={5}
          maxDistance={15}
        />

      </Canvas>

    </div>
  )
}