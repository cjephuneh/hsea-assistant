// Audio worklet processor for playback
class PlaybackWorkletProcessor extends globalThis.AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.port.onmessage = (event) => {
      if (event.data === null) {
        this.buffer = [];
      } else {
        this.buffer.push(...event.data);
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs[0];
    if (output.length > 0) {
      const outputChannel = output[0];
      for (let i = 0; i < outputChannel.length; i++) {
        if (this.buffer.length > 0) {
          outputChannel[i] = this.buffer.shift() / 0x7FFF;
        } else {
          outputChannel[i] = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor("playback-worklet", PlaybackWorkletProcessor);
