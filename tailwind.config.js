const c = (v) => `rgb(var(--${v}) / <alpha-value>)`
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: { colors: { bg: c('bg'), card: c('card'), fg: c('fg'), mute: c('mute'), line: c('line'), accent: c('accent'), ok: c('ok'), warn: c('warn'), bad: c('bad') } } },
}
