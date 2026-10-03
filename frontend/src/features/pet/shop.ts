import type { ImageSourcePropType } from 'react-native'

export interface FoodItem {
  id: string
  name: string
  category: 'daily' | 'treat'
  price: number
  fullness: number
  happiness: number
  image?: ImageSourcePropType
  art?: 'hay' | 'grass'
}

export const FOOD_ITEMS: FoodItem[] = [
  {
    id: 'hay',
    name: 'Hay',
    category: 'daily',
    price: 6,
    fullness: 20,
    happiness: 4,
    art: 'hay',
  },
  {
    id: 'grass',
    name: 'Fresh grass',
    category: 'daily',
    price: 4,
    fullness: 12,
    happiness: 4,
    art: 'grass',
  },
  {
    id: 'celery',
    name: 'Celery',
    category: 'daily',
    price: 6,
    fullness: 8,
    happiness: 4,
    image: require('../../../assets/pet/food/celery-stick.png'),
  },
  {
    id: 'carrot',
    name: 'Carrot',
    category: 'treat',
    price: 5,
    fullness: 10,
    happiness: 5,
    image: require('../../../assets/pet/food/carrot.png'),
  },
  {
    id: 'apple',
    name: 'Apple',
    category: 'treat',
    price: 8,
    fullness: 12,
    happiness: 8,
    image: require('../../../assets/pet/food/apple.png'),
  },
  {
    id: 'broccoli',
    name: 'Broccoli',
    category: 'treat',
    price: 10,
    fullness: 14,
    happiness: 6,
    image: require('../../../assets/pet/food/broccoli.png'),
  },
  {
    id: 'strawberry',
    name: 'Strawberry',
    category: 'treat',
    price: 15,
    fullness: 6,
    happiness: 14,
    image: require('../../../assets/pet/food/strawberry.png'),
  },
]
