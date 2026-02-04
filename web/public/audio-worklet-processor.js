// Audio worklet processor for recording audio at 24kHz
class AudioWorkletProcessor extends globalThis.AudioWorkletProcessor {
  constructor() {
    super();
  }

  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const inputChannel = input[0];
      const int16Array = new Int16Array(inputChannel.length);
      for (let i = 0; i < inputChannel.length; i++) {
        const s = Math.max(-1, Math.min(1, inputChannel[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      this.port.postMessage({ buffer: int16Array.buffer });
    }
    return true;
  }
}

registerProcessor("audio-worklet-processor", AudioWorkletProcessor);
