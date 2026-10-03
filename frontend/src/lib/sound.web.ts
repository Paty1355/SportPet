import { isSoundMuted } from './soundSettings'

export { useSoundOn } from './soundSettings'

const petUrl: string = require('../../assets/sounds/pet.wav')
const munchUrl: string = require('../../assets/sounds/munch.wav')

let context: AudioContext | null = null
const buffers = new Map<string, Promise<AudioBuffer>>()

function getContext(): AudioContext {
  if (!context) context = new AudioContext()
  return context
}

function load(url: string): Promise<AudioBuffer> {
  let pending = buffers.get(url)
  if (!pending) {
    pending = fetch(url)
      .then((response) => response.arrayBuffer())
      .then((data) => getContext().decodeAudioData(data))
    buffers.set(url, pending)
  }
  return pending
}

export function preloadSounds() {
  load(petUrl).catch(() => {})
  load(munchUrl).catch(() => {})
}

function play(url: string) {
  if (isSoundMuted()) return
  const ctx = getContext()
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  load(url)
    .then((buffer) => {
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      source.start()
    })
    .catch(() => {})
}

export function playPetSound() {
  play(petUrl)
}

export function playMunchSound() {
  play(munchUrl)
}
