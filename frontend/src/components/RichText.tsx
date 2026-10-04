import { StyleSheet, Text, View, type TextStyle } from 'react-native'

interface Part {
  text: string
  bold?: boolean
  italic?: boolean
}

const INLINE = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*)/

function parseInline(line: string): Part[] {
  return line
    .split(INLINE)
    .filter((chunk) => chunk !== '')
    .map((chunk) => {
      if (chunk.startsWith('**') && chunk.endsWith('**') && chunk.length > 4) {
        return { text: chunk.slice(2, -2), bold: true }
      }
      if (chunk.startsWith('*') && chunk.endsWith('*') && chunk.length > 2) {
        return { text: chunk.slice(1, -1), italic: true }
      }
      return { text: chunk }
    })
}

function renderParts(parts: Part[]) {
  return parts.map((part, index) => (
    <Text
      key={index}
      style={{
        fontWeight: part.bold ? '700' : undefined,
        fontStyle: part.italic ? 'italic' : undefined,
      }}
    >
      {part.text}
    </Text>
  ))
}

export function RichText({ text, style, color }: { text: string; style?: TextStyle; color: string }) {
  const lines = text.split('\n')

  return (
    <View style={styles.container}>
      {lines.map((raw, index) => {
        if (raw.trim() === '') return <View key={index} style={styles.gap} />

        const bullet = raw.match(/^\s*[-*•]\s+(.*)$/)
        const numbered = raw.match(/^\s*(\d+)[.)]\s+(.*)$/)

        if (bullet || numbered) {
          const marker = bullet ? '•' : `${numbered![1]}.`
          const content = bullet ? bullet[1] : numbered![2]
          return (
            <View key={index} style={styles.listRow}>
              <Text style={[style, { color, minWidth: 18 }]}>{marker}</Text>
              <Text style={[style, { color, flex: 1 }]}>{renderParts(parseInline(content))}</Text>
            </View>
          )
        }

        return (
          <Text key={index} style={[style, { color }]}>
            {renderParts(parseInline(raw))}
          </Text>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: 4 },
  gap: { height: 6 },
  listRow: { flexDirection: 'row', gap: 6 },
})
