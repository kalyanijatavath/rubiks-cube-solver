# Rubik's Cube Solver

A browser-based Rubik's Cube solver built with Next.js. Point your webcam at each face of a scrambled cube, let an on-device ML model read the sticker colours, fix any mistakes by hand, and get a step-by-step solution that plays back on an interactive 3D cube.

**Live demo:** [rubikscubesolver3d.netlify.app](https://rubikscubesolver3d.netlify.app/)

## Features

- **Webcam scanning** – guided capture of all six faces (front → right → back → left → up → down) with orientation hints for each step. Works with front or rear camera.
- **ML colour detection** – an ONNX model (`public/model/model.onnx`) runs fully in the browser via `onnxruntime-web` and classifies each of the 9 stickers per face into white, yellow, red, orange, blue or green.
- **Manual colour correction** – click any sticker to change its colour before saving the face. A live counter shows how many of each colour have been used (every colour must appear exactly 9 times).
- **Validation** – checks that all faces are scanned and the colour counts are consistent before solving.
- **Kociemba solver** – converts the scanned state to Kociemba notation (U R F D L B) and computes a short solution using `rubik-cube-solver`.
- **3D visualisation** – a React Three Fiber cube animates each move; step forward/back or auto-play the whole solution.

## Tech stack

| Area | Tools |
| --- | --- |
| Framework | Next.js 16 (App Router), React 19, TypeScript |
| Styling | Tailwind CSS 4 |
| Camera | `react-webcam` |
| Colour model | ONNX Runtime Web (WASM) |
| Solver | `rubik-cube-solver` (Kociemba two-phase) |
| 3D | Three.js, `@react-three/fiber`, `@react-three/drei` |
| Hosting | Netlify (`@netlify/plugin-nextjs`) |

## Getting started

Requirements: Node.js 20+ and npm.

```bash
git clone https://github.com/kalyanijatavath/rubiks-cube-solver.git
cd rubiks-cube-solver
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Camera access requires `localhost` or HTTPS.

Other scripts:

```bash
npm run build   # production build
npm run start   # serve the production build
npm run lint    # ESLint
```

## How to use

1. Wait for the colour model to finish loading, then start the camera.
2. Hold the cube as the on-screen guide describes (centre colour facing the camera, given colour on top) and capture the face.
3. Check the detected colours; click stickers to correct them, then confirm.
4. Repeat for all six faces. Use **Back** or **Rescan** if something goes wrong.
5. Press **Solve** and follow the moves on the 3D cube, one step at a time or with auto-play.

Colour convention used by the solver: white = Up, yellow = Down, green = Front, blue = Back, orange = Left, red = Right.

## Project structure

```
public/
  model/model.onnx        # sticker colour classifier
src/
  app/                    # layout, global styles, main page
  components/
    WebcamSection.tsx     # camera feed + capture
    ScanGuide.tsx         # per-face orientation instructions
    Cube3D.tsx            # 3D cube and move animation
    SolutionDisplay.tsx   # move list / playback
  hooks/
    useCubeState.ts       # scanned faces, scan order, progress
    useWebcam.ts          # camera control and screenshots
  lib/
    colorClassifier.ts    # ONNX model loading and inference
    cubeUtils.ts          # splits a frame into 9 stickers and predicts colours
    cubeSolver.ts         # validation, Kociemba conversion, solving, move application
netlify.toml              # Netlify build config
```

## Deployment

The app is live on Netlify at https://rubikscubesolver3d.netlify.app/.

The repo includes `netlify.toml` for Netlify: connect the repository, keep the build command `npm run build`, and the Next.js plugin handles the rest. It can also be deployed to Vercel with no extra configuration.

## Notes

- Lighting matters: scan in even, bright light and avoid glare on the stickers for the best detection accuracy.
- All image processing happens on your device; no frames are uploaded anywhere.
