class PCMProcessor extends AudioWorkletProcessor {
  process(inputs) {
    if (!inputs.length || !inputs[0].length || !inputs[0][0]) return true;

    const float32 = inputs[0][0];
    const pcm16 = new Int16Array(float32.length);

    for (let i = 0; i < float32.length; i++) {
      const v = Math.max(-1, Math.min(1, float32[i]));
      pcm16[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }

    this.port.postMessage(pcm16);
    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
