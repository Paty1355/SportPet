import { Ionicons } from '@expo/vector-icons'
import { Link } from 'expo-router'
import { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Screen } from '../../components/Screen'
import Svg from 'react-native-svg'
import { useTheme } from '../../lib/theme'
import { COSMETICS, type CosmeticItem, type CosmeticKind } from './cosmetics'
import { DecorPreview } from './Decor'
import { FoodArt } from './FoodArt'
import { HatLayer } from './PetCharacter'
import { usePet } from './PetProvider'
import { ownedCount, ownsCosmetic, type PetState } from './petLogic'
import { FOOD_ITEMS, type FoodItem } from './shop'

type Tab = 'food' | CosmeticKind

const TABS: { id: Tab; label: string }[] = [
  { id: 'food', label: 'Food' },
  { id: 'hat', label: 'Hats' },
  { id: 'background', label: 'Backgrounds' },
  { id: 'body', label: 'Colors' },
  { id: 'decor', label: 'Accessories' },
  { id: 'theme', label: 'Themes' },
]

export function ShopScreen() {
  const { colors } = useTheme()
  const { pet, buy, buyCosmetic, equipCosmetic } = usePet()
  const [tab, setTab] = useState<Tab>('food')

  return (
    <Screen>
      <View style={styles.topRow}>
        <Link href="/pet" asChild>
          <Pressable accessibilityRole="link" style={styles.back}>
            <Ionicons name="chevron-back" size={18} color={colors.primary} />
            <Text style={[styles.backText, { color: colors.primary }]}>Back to Bun</Text>
          </Pressable>
        </Link>
        <View style={[styles.coinChip, { backgroundColor: colors.warnSoft }]}>
          <Ionicons name="barbell" size={16} color={colors.warn} />
          <Text style={[styles.coinText, { color: colors.warn }]}>{pet?.coins ?? 0}</Text>
        </View>
      </View>

      <View style={styles.tabs}>
        {TABS.map((item) => {
          const active = item.id === tab
          return (
            <Pressable
              key={item.id}
              onPress={() => setTab(item.id)}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              style={[
                styles.tab,
                { backgroundColor: active ? colors.primary : colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.tabText, { color: active ? '#ffffff' : colors.text }]}>{item.label}</Text>
            </Pressable>
          )
        })}
      </View>

      {pet && tab === 'food' &&
        FOOD_ITEMS.map((food) => (
          <FoodRow key={food.id} food={food} owned={ownedCount(pet, food.id)} coins={pet.coins} onBuy={() => buy(food)} />
        ))}

      {pet &&
        tab !== 'food' &&
        COSMETICS.filter((item) => item.kind === tab).map((item) => (
          <CosmeticRow
            key={item.id}
            item={item}
            pet={pet}
            onBuy={() => buyCosmetic(item)}
            onEquip={() => equipCosmetic(item)}
          />
        ))}
    </Screen>
  )
}

function FoodRow({ food, owned, coins, onBuy }: { food: FoodItem; owned: number; coins: number; onBuy: () => void }) {
  const { colors } = useTheme()
  const affordable = coins >= food.price

  return (
    <View style={[styles.row, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <FoodArt food={food} size={52} />
      <View style={styles.info}>
        <Text style={[styles.name, { color: colors.text }]}>{food.name}</Text>
        <Text style={[styles.effect, { color: colors.muted }]}>
          {food.category === 'daily' ? 'Daily food' : 'Treat, small portions'} · +{food.fullness} fullness · owned {owned}
        </Text>
      </View>
      <PriceButton price={food.price} enabled={affordable} onPress={onBuy} label={String(food.price)} />
    </View>
  )
}

function CosmeticRow({
  item,
  pet,
  onBuy,
  onEquip,
}: {
  item: CosmeticItem
  pet: PetState
  onBuy: () => void
  onEquip: () => void
}) {
  const { colors } = useTheme()
  const owned = ownsCosmetic(pet, item.id)
  const equipped =
    item.kind === 'hat'
      ? pet.equipped.hat === item.id
      : item.kind === 'background'
        ? pet.equipped.background === item.id
        : item.kind === 'decor'
          ? pet.equipped.decor.includes(item.id)
          : item.kind === 'theme'
            ? pet.equipped.theme === item.id
            : pet.equipped.body === item.id

  return (
    <View style={[styles.row, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Swatch item={item} />
      <View style={styles.info}>
        <Text style={[styles.name, { color: colors.text }]}>{item.name}</Text>
        <Text style={[styles.effect, { color: colors.muted }]}>
          {owned ? (equipped ? 'Equipped' : 'Owned') : `${item.price} hantelek`}
        </Text>
      </View>
      {owned ? (
        <Pressable
          onPress={onEquip}
          disabled={item.kind !== 'hat' && item.kind !== 'decor' && equipped}
          accessibilityRole="button"
          style={[
            styles.buy,
            {
              backgroundColor:
                equipped && item.kind !== 'hat' && item.kind !== 'decor' ? colors.neutralSoft : colors.primary,
            },
          ]}
        >
          <Text
            style={[
              styles.buyText,
              {
                color:
                  equipped && item.kind !== 'hat' && item.kind !== 'decor' ? colors.muted : '#ffffff',
              },
            ]}
          >
            {item.kind === 'hat'
              ? equipped
                ? 'Take off'
                : 'Wear'
              : item.kind === 'decor'
                ? equipped
                  ? 'Hide'
                  : 'Show'
                : equipped
                  ? 'In use'
                  : 'Use'}
          </Text>
        </Pressable>
      ) : (
        <PriceButton price={item.price} enabled={pet.coins >= item.price} onPress={onBuy} label={String(item.price)} />
      )}
    </View>
  )
}

function Swatch({ item }: { item: CosmeticItem }) {
  const { colors } = useTheme()
  if (item.kind === 'hat') {
    return (
      <View style={[styles.swatch, { backgroundColor: colors.primarySoft }]}>
        <Svg width={48} height={40} viewBox="40 10 140 110">
          <HatLayer id={item.id} />
        </Svg>
      </View>
    )
  }
  if (item.kind === 'decor') {
    return (
      <View style={[styles.swatch, { backgroundColor: colors.primarySoft }]}>
        <DecorPreview id={item.id} />
      </View>
    )
  }
  const palette = item.palette ?? []
  return (
    <View style={styles.swatchRow}>
      {palette.slice(0, item.kind === 'background' ? 2 : 1).map((color) => (
        <View key={color} style={[styles.dot, { backgroundColor: color }]} />
      ))}
    </View>
  )
}

function PriceButton({
  price,
  enabled,
  onPress,
  label,
}: {
  price: number
  enabled: boolean
  onPress: () => void
  label: string
}) {
  const { colors } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      disabled={!enabled}
      accessibilityRole="button"
      style={[styles.buy, { backgroundColor: enabled ? colors.primary : colors.neutralSoft }]}
    >
      <Ionicons name="barbell" size={14} color={enabled ? '#ffffff' : colors.muted} />
      <Text style={[styles.buyText, { color: enabled ? '#ffffff' : colors.muted }]}>{price || label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 },
  back: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  backText: { fontSize: 15, fontWeight: '600' },
  coinChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999 },
  coinText: { fontSize: 15, fontWeight: '700' },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tab: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: StyleSheet.hairlineWidth },
  tabText: { fontSize: 13, fontWeight: '700' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 18, borderWidth: StyleSheet.hairlineWidth },
  icon: { width: 52, height: 52 },
  swatch: { width: 52, height: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  swatchRow: { flexDirection: 'row', width: 52, height: 52, alignItems: 'center', justifyContent: 'center', gap: 4 },
  dot: { width: 22, height: 22, borderRadius: 11 },
  info: { flex: 1, gap: 2 },
  name: { fontSize: 16, fontWeight: '700' },
  effect: { fontSize: 12 },
  buy: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12 },
  buyText: { fontSize: 15, fontWeight: '700' },
})
