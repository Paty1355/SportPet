import { createAudioPlayer, type AudioPlayer } from 'expo-audio'
import { isSoundMuted } from './soundSettings'

export { useSoundOn } from './soundSettings'

const petSound = require('../../assets/sounds/pet.wav')
const munchSound = require('../../assets/sounds/munch.wav')

const players = new Map<number, AudioPlayer>()

function getPlayer(source: number): AudioPlayer {
  let player = players.get(source)
  if (!player) {
    player = createAudioPlayer(source)
    players.set(source, player)
  }
  return player
}

export function preloadSounds() {
  getPlayer(petSound)
  getPlayer(munchSound)
}

function play(source: number) {
  if (isSoundMuted()) return
  const player = getPlayer(source)
  if (player.playing) player.seekTo(0)
  player.play()
}

export function playPetSound() {
  play(petSound)
}

export function playMunchSound() {
  play(munchSound)
}
