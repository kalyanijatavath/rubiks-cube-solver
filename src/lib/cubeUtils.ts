'use client'

import * as ort from 'onnxruntime-web'

const COLOR_NAMES = ['blue', 'green', 'orange', 'red', 'white', 'yellow'] as const
export type ColorName = typeof COLOR_NAMES[number]

let session: ort.InferenceSession | null = null
let isLoading = false

export async function loadModel(): Promise<boolean> {
  if (session) return true
  if (isLoading) return false
  isLoading = true
  
  try {
    session = await ort.InferenceSession.create('/model/model.onnx', { executionProviders: ['wasm'] })
    console.log('Model loaded successfully!')
    isLoading = false
    return true
  } catch (error) {
    console.error('Failed to load model:', error)
    isLoading = false
    return false
  }
}

export function isModelLoaded(): boolean {
  return session !== null
}

function preprocessImage(imageData: ImageData): Float32Array {
  const { data, width, height } = imageData
  const inputSize = 224
  const output = new Float32Array(1 * 3 * inputSize * inputSize)
  
  for (let c = 0; c < 3; c++) {
    for (let y = 0; y < inputSize; y++) {
      for (let x = 0; x < inputSize; x++) {
        const srcX = Math.floor(x * width / inputSize)
        const srcY = Math.floor(y * height / inputSize)
        const srcIdx = (srcY * width + srcX) * 4
        let value = data[srcIdx + c] / 255.0
        const mean = [0.485, 0.456, 0.406][c]
        const std = [0.229, 0.224, 0.225][c]
        value = (value - mean) / std
        output[c * inputSize * inputSize + y * inputSize + x] = value
      }
    }
  }
  return output
}

function softmax(arr: Float32Array): Float32Array {
  const result = new Float32Array(arr.length)
  const max = Math.max(...arr)
  let sum = 0
  for (let i = 0; i < arr.length; i++) { result[i] = Math.exp(arr[i] - max); sum += result[i] }
  for (let i = 0; i < arr.length; i++) result[i] /= sum
  return result
}

export async function predictColor(imageData: ImageData): Promise<{ color: ColorName; confidence: number }> {
  if (!session) throw new Error('Model not loaded')
  const inputData = preprocessImage(imageData)
  const tensor = new ort.Tensor('float32', inputData, [1, 3, 224, 224])
  const results = await session.run({ input: tensor })
  const output = results.output.data as Float32Array
  const probabilities = softmax(output)
  
  let maxIdx = 0, maxProb = probabilities[0]
  for (let i = 1; i < probabilities.length; i++) {
    if (probabilities[i] > maxProb) { maxProb = probabilities[i]; maxIdx = i }
  }
  return { color: COLOR_NAMES[maxIdx], confidence: maxProb }
}

function extractRegion(imageData: ImageData, startX: number, startY: number, width: number, height: number): ImageData {
  const regionData = new Uint8ClampedArray(width * height * 4)
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const srcIdx = ((startY + y) * imageData.width + (startX + x)) * 4
      const dstIdx = (y * width + x) * 4
      regionData[dstIdx] = imageData.data[srcIdx]
      regionData[dstIdx + 1] = imageData.data[srcIdx + 1]
      regionData[dstIdx + 2] = imageData.data[srcIdx + 2]
      regionData[dstIdx + 3] = imageData.data[srcIdx + 3]
    }
  }
  return new ImageData(regionData, width, height)
}

export function extractStickersFromImage(imageData: ImageData, gridSize: number = 240): ImageData[] {
  const stickers: ImageData[] = []
  const gridStartX = Math.floor((imageData.width - gridSize) / 2)
  const gridStartY = Math.floor((imageData.height - gridSize) / 2)
  const stickerSize = Math.floor(gridSize / 3)
  
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const startX = gridStartX + col * stickerSize
      const startY = gridStartY + row * stickerSize
      const margin = Math.floor(stickerSize * 0.15)
      const extractSize = stickerSize - 2 * margin
      stickers.push(extractRegion(imageData, startX + margin, startY + margin, extractSize, extractSize))
    }
  }
  return stickers
}

export async function base64ToImageData(base64: string): Promise<ImageData> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext('2d')
      if (!ctx) { reject(new Error('Could not get canvas context')); return }
      ctx.drawImage(img, 0, 0)
      resolve(ctx.getImageData(0, 0, img.width, img.height))
    }
    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = base64
  })
}

function flipStickersHorizontally(colors: ColorName[]): ColorName[] {
  return [colors[2], colors[1], colors[0], colors[5], colors[4], colors[3], colors[8], colors[7], colors[6]]
}

export async function predictFaceColors(
  imageBase64: string,
  shouldFlip: boolean
): Promise<ColorName[]> {
  if (!isModelLoaded()) {
    const loaded = await loadModel()
    if (!loaded) throw new Error('Failed to load model')
  }
  
  const imageData = await base64ToImageData(imageBase64)
  const stickerImages = extractStickersFromImage(imageData)
  const colors: ColorName[] = []
  
  for (let i = 0; i < 9; i++) {
    const result = await predictColor(stickerImages[i])
    colors.push(result.color)
    console.log(`Sticker ${i + 1}: ${result.color} (${(result.confidence * 100).toFixed(1)}%)`)
  }
  
  return shouldFlip ? flipStickersHorizontally(colors) : colors
}

export async function initColorDetection(): Promise<boolean> {
  console.log('Initializing color detection model...')
  return await loadModel()
}

export function isColorDetectionReady(): boolean {
  return isModelLoaded()
}