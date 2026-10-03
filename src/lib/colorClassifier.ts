'use client'

import * as ort from 'onnxruntime-web'

// Color names in order (must match your training data)
const COLOR_NAMES = ['blue', 'green', 'orange', 'red', 'white', 'yellow'] as const
export type ColorName = typeof COLOR_NAMES[number]

// Model state
let session: ort.InferenceSession | null = null
let isLoading = false

/**
 * Load the ONNX model
 */
export async function loadModel(): Promise<boolean> {
  if (session) return true
  if (isLoading) return false
  
  isLoading = true
  
  try {
    // Create inference session
    session = await ort.InferenceSession.create('/model/model.onnx', {
      executionProviders: ['wasm']
    })
    console.log('Model loaded successfully!')
    isLoading = false
    return true
  } catch (error) {
    console.error('Failed to load model:', error)
    isLoading = false
    return false
  }
}

/**
 * Check if model is loaded
 */
export function isModelLoaded(): boolean {
  return session !== null
}

/**
 * Preprocess image for model input
 */
function preprocessImage(imageData: ImageData): Float32Array {
  const { data, width, height } = imageData
  const inputSize = 224
  
  // Create output array (1, 3, 224, 224)
  const output = new Float32Array(1 * 3 * inputSize * inputSize)
  
  // Simple resize and normalize
  for (let c = 0; c < 3; c++) {
    for (let y = 0; y < inputSize; y++) {
      for (let x = 0; x < inputSize; x++) {
        // Map to source coordinates
        const srcX = Math.floor(x * width / inputSize)
        const srcY = Math.floor(y * height / inputSize)
        
        // Get source pixel
        const srcIdx = (srcY * width + srcX) * 4
        let value = data[srcIdx + c] / 255.0
        
        // Normalize (ImageNet)
        const mean = [0.485, 0.456, 0.406][c]
        const std = [0.229, 0.224, 0.225][c]
        value = (value - mean) / std
        
        // Set output (CHW format)
        output[c * inputSize * inputSize + y * inputSize + x] = value
      }
    }
  }
  
  return output
}

/**
 * Softmax function
 */
function softmax(arr: Float32Array): Float32Array {
  const result = new Float32Array(arr.length)
  const max = Math.max(...arr)
  let sum = 0
  
  for (let i = 0; i < arr.length; i++) {
    result[i] = Math.exp(arr[i] - max)
    sum += result[i]
  }
  
  for (let i = 0; i < arr.length; i++) {
    result[i] /= sum
  }
  
  return result
}

/**
 * Predict color from image data
 */
export async function predictColor(imageData: ImageData): Promise<{ color: ColorName; confidence: number }> {
  if (!session) {
    throw new Error('Model not loaded. Call loadModel() first.')
  }
  
  // Preprocess image
  const inputData = preprocessImage(imageData)
  
  // Create tensor
  const tensor = new ort.Tensor('float32', inputData, [1, 3, 224, 224])
  
  // Run inference
  const feeds = { input: tensor }
  const results = await session.run(feeds)
  
  // Get output
  const output = results.output.data as Float32Array
  
  // Apply softmax
  const probabilities = softmax(output)
  
  // Get max probability
  let maxIdx = 0
  let maxProb = probabilities[0]
  for (let i = 1; i < probabilities.length; i++) {
    if (probabilities[i] > maxProb) {
      maxProb = probabilities[i]
      maxIdx = i
    }
  }
  
  return {
    color: COLOR_NAMES[maxIdx],
    confidence: maxProb
  }
}

/**
 * Get list of color names
 */
export function getColorNames(): readonly ColorName[] {
  return COLOR_NAMES
}