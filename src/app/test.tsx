{/* Color Correction Mode */}
<div className="flex-1 bg-gray-900 rounded-lg p-4 flex flex-col">
  <h3 className="text-lg font-semibold mb-2 text-yellow-400">
    🎨 Correct Colors (if needed)
  </h3>
  ...
  
  {/* Confirm Button */}
  <div className="flex gap-2 justify-center">
    <button
      onClick={handleConfirm}
      className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors font-medium"
    >
      ✓ Confirm & Continue
    </button>
    <button
      onClick={() => setEditingColors(null)}
      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg transition-colors font-medium"
    >
      🔄 Rescan Face
    </button>
  </div>
</div>