class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      // input[0] = Float32Array of PCM samples
      this.port.postMessage(input[0]);
    }
    return true; // keep processor alive
  }
}

registerProcessor("pcm-processor", PCMProcessor);
