import {
  AudioLines,
  Captions,
  Crop,
  MicOff,
  Palette,
  Scissors,
  Timer,
  VolumeX,
} from 'lucide-react'
import { FeatureCard } from './FeatureCard'
import type { EditOptions } from '../types'

interface Props {
  options: EditOptions
  onChange: (next: EditOptions) => void
}

export function FeatureDashboard({ options, onChange }: Props) {
  const set = <K extends keyof EditOptions>(key: K, value: EditOptions[K]) => {
    onChange({ ...options, [key]: value })
  }

  return (
    <section className="features">
      <div className="section-head">
        <h2>Choose what AI should edit</h2>
        <p>Enable any combination. Only selected stages will run.</p>
      </div>

      <div className="feature-grid">
        <FeatureCard
          title="Background Noise"
          description="Remove fan, traffic, keyboard, AC, hiss, and hum while preserving voice."
          icon={<MicOff size={20} />}
          enabled={options.noise.enabled}
          onToggle={(enabled) => set('noise', { ...options.noise, enabled })}
        >
          <label className="field">
            <span>Noise reduction strength</span>
            <select
              value={options.noise.strength}
              onChange={(e) =>
                set('noise', { ...options.noise, strength: e.target.value as EditOptions['noise']['strength'] })
              }
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
        </FeatureCard>

        <FeatureCard
          title="Long Silences"
          description="Cut unnecessary silent gaps. Natural short pauses between words are kept."
          icon={<VolumeX size={20} />}
          enabled={options.silence.enabled}
          onToggle={(enabled) => set('silence', { ...options.silence, enabled })}
        >
          <label className="field">
            <span>Preset</span>
            <select
              value={options.silence.preset}
              onChange={(e) =>
                set('silence', {
                  ...options.silence,
                  preset: e.target.value as EditOptions['silence']['preset'],
                })
              }
            >
              <option value="conservative">Conservative</option>
              <option value="balanced">Balanced</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </label>
        </FeatureCard>

        <FeatureCard
          title="Captions"
          description="Transcribe speech with timestamps and burn styled subtitles into the video."
          icon={<Captions size={20} />}
          enabled={options.captions.enabled}
          onToggle={(enabled) => set('captions', { ...options.captions, enabled })}
          badge="AI"
        >
          <div className="field-row">
            <label className="field">
              <span>Language</span>
              <select
                value={options.captions.language}
                onChange={(e) => set('captions', { ...options.captions, language: e.target.value })}
              >
                <option value="auto">Auto-detect</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="hi">Hindi</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </label>
            <label className="field">
              <span>Style</span>
              <select
                value={options.captions.style}
                onChange={(e) =>
                  set('captions', {
                    ...options.captions,
                    style: e.target.value as EditOptions['captions']['style'],
                  })
                }
              >
                <option value="clean">Clean</option>
                <option value="bold">Bold</option>
                <option value="modern">Modern</option>
                <option value="minimal">Minimal</option>
                <option value="social">Social Media</option>
                <option value="highlighted">Highlighted Words</option>
              </select>
            </label>
          </div>
          <div className="field-row">
            <label className="field">
              <span>Font size</span>
              <input
                type="number"
                min={24}
                max={96}
                value={options.captions.font_size}
                onChange={(e) =>
                  set('captions', { ...options.captions, font_size: Number(e.target.value) })
                }
              />
            </label>
            <label className="field">
              <span>Position</span>
              <select
                value={options.captions.position}
                onChange={(e) =>
                  set('captions', {
                    ...options.captions,
                    position: e.target.value as EditOptions['captions']['position'],
                  })
                }
              >
                <option value="bottom">Bottom</option>
                <option value="center">Center</option>
                <option value="top">Top</option>
              </select>
            </label>
          </div>
          <div className="field-row">
            <label className="field">
              <span>Color</span>
              <input
                type="color"
                value={options.captions.color.slice(0, 7)}
                onChange={(e) => set('captions', { ...options.captions, color: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Highlight</span>
              <input
                type="color"
                value={options.captions.highlight_color.slice(0, 7)}
                onChange={(e) =>
                  set('captions', { ...options.captions, highlight_color: e.target.value })
                }
              />
            </label>
          </div>
        </FeatureCard>

        <FeatureCard
          title="Color Grading"
          description="Apply cinematic looks or auto-correct brightness, contrast, and temperature."
          icon={<Palette size={20} />}
          enabled={options.color.enabled}
          onToggle={(enabled) => set('color', { ...options.color, enabled })}
        >
          <label className="check">
            <input
              type="checkbox"
              checked={options.color.auto_color}
              onChange={(e) => set('color', { ...options.color, auto_color: e.target.checked })}
            />
            Auto Color
          </label>
          <label className="field">
            <span>Preset</span>
            <select
              value={options.color.preset}
              onChange={(e) =>
                set('color', { ...options.color, preset: e.target.value as EditOptions['color']['preset'] })
              }
            >
              <option value="natural">Natural</option>
              <option value="cinematic">Cinematic</option>
              <option value="warm">Warm</option>
              <option value="cool">Cool</option>
              <option value="vibrant">Vibrant</option>
              <option value="moody">Moody</option>
              <option value="high_contrast">High Contrast</option>
              <option value="auto">Auto</option>
            </select>
          </label>
          <div className="sliders">
            {(
              [
                ['brightness', -0.5, 0.5, 0.01],
                ['contrast', 0.5, 1.8, 0.01],
                ['saturation', 0.2, 2, 0.01],
                ['temperature', -1, 1, 0.01],
              ] as const
            ).map(([key, min, max, step]) => (
              <label key={key} className="field">
                <span>
                  {key} <em>{Number(options.color[key]).toFixed(2)}</em>
                </span>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={options.color[key]}
                  onChange={(e) => set('color', { ...options.color, [key]: Number(e.target.value) })}
                />
              </label>
            ))}
          </div>
        </FeatureCard>

        <FeatureCard
          title="Filler Words"
          description="Detect um, uh, hmm, and similar fillers. Never blindly remove meaning-bearing words."
          icon={<AudioLines size={20} />}
          enabled={options.filler.enabled}
          onToggle={(enabled) => set('filler', { ...options.filler, enabled })}
          badge="AI"
        >
          <label className="field">
            <span>Action</span>
            <select
              value={options.filler.mode}
              onChange={(e) =>
                set('filler', { ...options.filler, mode: e.target.value as EditOptions['filler']['mode'] })
              }
            >
              <option value="keep">Keep</option>
              <option value="remove">Remove automatically</option>
              <option value="review">Review before removing</option>
            </select>
          </label>
        </FeatureCard>

        <FeatureCard
          title="Auto Reframe"
          description="Reframe for 16:9, 9:16, or 1:1 while keeping the subject centered."
          icon={<Crop size={20} />}
          enabled={options.reframe.enabled}
          onToggle={(enabled) => set('reframe', { ...options.reframe, enabled })}
        >
          <label className="field">
            <span>Output format</span>
            <select
              value={options.reframe.aspect}
              onChange={(e) =>
                set('reframe', {
                  ...options.reframe,
                  aspect: e.target.value as EditOptions['reframe']['aspect'],
                })
              }
            >
              <option value="16:9">16:9 Landscape</option>
              <option value="9:16">9:16 TikTok / Reels</option>
              <option value="1:1">1:1 Square</option>
            </select>
          </label>
        </FeatureCard>

        <FeatureCard
          title="Jump Cuts"
          description="Clean jump cuts for dead air and unusable gaps without chopping meaningful speech."
          icon={<Scissors size={20} />}
          enabled={options.jump_cuts.enabled}
          onToggle={(enabled) => set('jump_cuts', { ...options.jump_cuts, enabled })}
        />

        <FeatureCard
          title="Unwanted Pauses"
          description="Shorten unnatural mid-sentence hesitations while keeping delivery natural."
          icon={<Timer size={20} />}
          enabled={options.pauses.enabled}
          onToggle={(enabled) => set('pauses', { ...options.pauses, enabled })}
        />
      </div>
    </section>
  )
}
