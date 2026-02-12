class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
  }

  process(inputs, outputs) {
    const input = inputs[0];
    
    if (!input || input.length === 0) return true;

    const channelData = input[0];
    
    // Convert Float32 to Int16
    const int16 = new Int16Array(channelData.length);
    for (let i = 0; i < channelData.length; i++) {
      const val = Math.max(-1, Math.min(1, channelData[i]));
      int16[i] = val < 0 ? val * 0x8000 : val * 0x7FFF;
    }
    
    // Send the Int16Array directly
    this.port.postMessage(int16);
    
    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);