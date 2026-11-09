<template>
  <div class="live-page">
    <el-row :gutter="16">
      <el-col :span="7">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>直播会话</span>
              <el-tag v-if="snapshot" size="small" :type="snapshot.status === 'ended' ? 'info' : 'success'">
                {{ snapshot.status === 'ended' ? '已结束' : '进行中' }}
              </el-tag>
            </div>
          </template>

          <el-form label-width="76px" size="default">
            <el-form-item label="直播间">
              <el-input v-model="createForm.roomId" placeholder="如 room-2026" />
            </el-form-item>
            <el-form-item label="直播标题">
              <el-input v-model="createForm.title" placeholder="如 秋冬衬衫专场" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="creating" @click="handleCreate">
                创建会话
              </el-button>
              <el-button
                v-if="snapshot && snapshot.status !== 'ended'"
                :loading="ending"
                @click="handleEnd"
              >
                结束会话
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider content-position="left">历史会话</el-divider>
          <el-table
            :data="sessions"
            size="small"
            v-loading="sessionLoading"
            @row-click="handleOpenSession"
          >
            <el-table-column prop="room_id" label="直播间" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="80" />
          </el-table>
          <el-empty
            v-if="!sessionLoading && sessions.length === 0"
            description="暂无会话"
            :image-size="50"
          />
        </el-card>
      </el-col>

      <el-col :span="17">
        <el-card v-if="snapshot">
          <template #header>
            <div class="card-header">
              <span>{{ snapshot.title || '未命名直播' }} · {{ snapshot.room_id }}</span>
              <span class="card-id">
                已处理字幕 {{ snapshot.processed_segments }} 条 / 弹幕
                {{ snapshot.processed_danmaku }} 条
              </span>
            </div>
          </template>

          <el-alert
            :title="snapshot.summary"
            type="info"
            :closable="false"
            show-icon
            class="summary-alert"
          />

          <el-card shadow="never" class="input-card">
            <template #header>推入一批直播事件</template>
            <el-form label-width="76px" size="default">
              <el-form-item label="口播字幕">
                <el-input
                  v-model="ingestForm.segments"
                  type="textarea"
                  :rows="2"
                  placeholder="每行一句口播，如：限量500件，拍一发三"
                />
              </el-form-item>
              <el-form-item label="弹幕">
                <el-input
                  v-model="ingestForm.danmaku"
                  type="textarea"
                  :rows="2"
                  placeholder="每行一条弹幕，如：冲了 / 太贵了"
                />
              </el-form-item>
              <el-form-item label="当前商品">
                <el-input v-model="ingestForm.product" placeholder="用于全网比价检索" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="ingesting" @click="handleIngest">
                  推入并刷新快照
                </el-button>
                <el-button :loading="refreshing" @click="handleRefresh">刷新快照</el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-card shadow="never" class="panel-card">
                <template #header>
                  关键信息（{{ snapshot.key_points.length }}）
                </template>
                <div class="tag-row">
                  <el-tag
                    v-for="(point, index) in snapshot.key_points"
                    :key="index"
                    :type="KIND_TYPE[point.kind]"
                    size="small"
                    effect="plain"
                  >
                    {{ KIND_LABEL[point.kind] }} · {{ point.text }}
                  </el-tag>
                  <span v-if="snapshot.key_points.length === 0" class="hint">
                    暂未从口播中捕捉到关键信息
                  </span>
                </div>
              </el-card>

              <el-card shadow="never" class="panel-card">
                <template #header>
                  弹幕口碑（{{ snapshot.sentiment.total }} 条 · 热度
                  {{ snapshot.sentiment.heat_per_minute.toFixed(1) }}/分钟）
                </template>
                <div class="sentiment-row">
                  <el-progress
                    type="circle"
                    :percentage="sentimentPercentage"
                    :width="90"
                    :color="sentimentColor"
                  >
                    <template #default>
                      <div class="sentiment-score">{{ snapshot.sentiment.score.toFixed(2) }}</div>
                      <div class="sentiment-label">情感分</div>
                    </template>
                  </el-progress>
                  <div class="sentiment-detail">
                    <div class="tag-row">
                      <el-tag
                        v-for="tag in snapshot.sentiment.tags"
                        :key="tag"
                        size="small"
                        :type="TAG_TYPE[tag] || 'info'"
                      >
                        {{ tag }}
                      </el-tag>
                    </div>
                    <p class="summary-text">
                      正向 {{ snapshot.sentiment.positive }} · 负向
                      {{ snapshot.sentiment.negative }} · 中性
                      {{ snapshot.sentiment.neutral }}
                    </p>
                    <p class="hint">
                      高频正向词：{{ snapshot.sentiment.top_positive_phrases.join('、') || '—' }}
                      <br />
                      高频负向词：{{ snapshot.sentiment.top_negative_phrases.join('、') || '—' }}
                    </p>
                  </div>
                </div>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card shadow="never" class="panel-card">
                <template #header>一键比价</template>
                <template v-if="snapshot.price_alert">
                  <el-alert
                    :title="snapshot.price_alert.advice"
                    :type="priceAlertType"
                    :closable="false"
                    show-icon
                  />
                  <el-descriptions :column="1" size="small" border class="price-desc">
                    <el-descriptions-item label="主播报价">
                      ¥{{ snapshot.price_alert.trigger.price.toFixed(2) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="全网最低">
                      ¥{{ snapshot.price_alert.comparison.lowest?.price.toFixed(2) ?? '—' }}
                    </el-descriptions-item>
                    <el-descriptions-item label="历史均价">
                      ¥{{ snapshot.price_alert.comparison.historical_avg?.toFixed(2) ?? '—' }}
                    </el-descriptions-item>
                  </el-descriptions>
                  <svg class="sparkline" viewBox="0 0 100 32" preserveAspectRatio="none">
                    <polyline
                      :points="sparkline"
                      fill="none"
                      stroke="#3b6df0"
                      stroke-width="1"
                    />
                  </svg>
                  <p class="hint">
                    数据源 {{ snapshot.price_alert.comparison.source }}
                    <template v-if="snapshot.price_alert.is_mock">（模拟数据，仅演示）</template>
                  </p>
                </template>
                <el-empty v-else description="主播报价后自动触发比价" :image-size="60" />
              </el-card>

              <el-card shadow="never" class="panel-card">
                <template #header>口播明细</template>
                <el-table :data="snapshot.key_points" size="small" max-height="220">
                  <el-table-column label="类型" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="KIND_TYPE[row.kind as KeyPointKind]">
                        {{ KIND_LABEL[row.kind as KeyPointKind] }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="text" label="内容" show-overflow-tooltip />
                  <el-table-column label="时间" width="80">
                    <template #default="{ row }">
                      {{ row.at_seconds === null ? '—' : `${row.at_seconds}s` }}
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </el-card>

        <el-card v-else>
          <el-empty description="创建或选择一个直播会话，推入字幕与弹幕即可实时摘要" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createSession,
  endSession,
  getSnapshot,
  ingestEvents,
  listSessions,
} from '@/api/live'
import type {
  DanmakuItem,
  KeyPointKind,
  LiveSessionSummary,
  LiveSnapshot,
  TranscriptSegment,
} from '@/types/live'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

const KIND_LABEL: Record<KeyPointKind, string> = {
  price: '价格',
  limit: '限量',
  gift: '赠品',
  deadline: '时效',
  spec: '规格',
  promise: '承诺',
  other: '其他',
}

const KIND_TYPE: Record<KeyPointKind, TagType> = {
  price: 'danger',
  limit: 'warning',
  gift: 'success',
  deadline: 'primary',
  spec: 'info',
  promise: 'info',
  other: 'info',
}

const TAG_TYPE: Record<string, TagType> = {
  口碑向好: 'success',
  口碑偏冷: 'danger',
  口碑中性: 'info',
  价格敏感: 'warning',
  购买意向强: 'success',
  热度高: 'danger',
  热度偏低: 'info',
}

const creating = ref(false)
const ingesting = ref(false)
const refreshing = ref(false)
const ending = ref(false)
const sessionLoading = ref(false)
const snapshot = ref<LiveSnapshot | null>(null)
const sessions = ref<LiveSessionSummary[]>([])

const createForm = reactive({
  roomId: 'room-2026',
  title: '秋冬衬衫专场',
})

const ingestForm = reactive({
  segments: '限量500件，拍一发三\n到手价199，只有今晚这个价',
  danmaku: '冲了冲了\n划算，已拍\n太贵了吧',
  product: '纯棉衬衫',
})

/** 情感分 -1~1 映射为进度条百分比 */
const sentimentPercentage = computed(() => {
  const score = snapshot.value?.sentiment.score ?? 0
  return Math.round(((score + 1) / 2) * 100)
})

const sentimentColor = computed(() => {
  const score = snapshot.value?.sentiment.score ?? 0
  if (score > 0.2) return '#10b981'
  if (score < -0.2) return '#ef4444'
  return '#f59e0b'
})

const priceAlertType = computed(() => {
  const verdict = snapshot.value?.price_alert?.comparison.verdict
  if (verdict === 'great_deal') return 'success'
  if (verdict === 'overpriced') return 'error'
  if (verdict === 'wait') return 'warning'
  return 'info'
})

const sparkline = computed(() => {
  const points = snapshot.value?.price_alert?.comparison.history ?? []
  if (points.length < 2) return ''
  const prices = points.map((point) => point.price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const span = max - min || 1
  return points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 100
      const y = 30 - ((point.price - min) / span) * 28
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
})

const splitLines = (value: string): string[] =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

/** 把多行口播文本按 10 秒一段切成字幕片段 */
const parseSegments = (value: string): TranscriptSegment[] =>
  splitLines(value).map((text, index) => ({
    start_seconds: index * 10,
    end_seconds: index * 10 + 8,
    text,
  }))

/** 把多行文本解析为弹幕 */
const parseDanmaku = (value: string): DanmakuItem[] =>
  splitLines(value).map((text) => ({ text }))

const handleCreate = async () => {
  if (!createForm.roomId) {
    ElMessage.warning('请填写直播间标识')
    return
  }
  creating.value = true
  try {
    const res = await createSession({
      room_id: createForm.roomId,
      title: createForm.title,
    })
    if (res.data.code === 200 && res.data.data) {
      snapshot.value = res.data.data
      ElMessage.success('会话已创建')
      fetchSessions()
    } else {
      ElMessage.error(res.data.message || '创建失败')
    }
  } catch {
    // 拦截器已提示
  } finally {
    creating.value = false
  }
}

const handleIngest = async () => {
  if (!snapshot.value) {
    ElMessage.warning('请先创建直播会话')
    return
  }
  const segments = parseSegments(ingestForm.segments)
  const danmaku = parseDanmaku(ingestForm.danmaku)
  if (!segments.length && !danmaku.length) {
    ElMessage.warning('请至少提供一条字幕或弹幕')
    return
  }
  ingesting.value = true
  try {
    const res = await ingestEvents(snapshot.value.session_id, {
      segments,
      danmaku,
      current_product: ingestForm.product || null,
    })
    if (res.data.code === 200 && res.data.data) {
      snapshot.value = res.data.data
      ElMessage.success('快照已更新')
    }
  } finally {
    ingesting.value = false
  }
}

const handleRefresh = async () => {
  if (!snapshot.value) return
  refreshing.value = true
  try {
    const res = await getSnapshot(snapshot.value.session_id)
    if (res.data.code === 200 && res.data.data) {
      snapshot.value = res.data.data
    }
  } finally {
    refreshing.value = false
  }
}

const handleEnd = async () => {
  if (!snapshot.value) return
  ending.value = true
  try {
    const res = await endSession(snapshot.value.session_id)
    if (res.data.code === 200 && res.data.data) {
      snapshot.value = res.data.data
      ElMessage.success('会话已结束')
      fetchSessions()
    }
  } finally {
    ending.value = false
  }
}

const fetchSessions = async () => {
  sessionLoading.value = true
  try {
    const res = await listSessions({ limit: 10 })
    if (res.data.code === 200 && Array.isArray(res.data.data)) {
      sessions.value = res.data.data
    }
  } finally {
    sessionLoading.value = false
  }
}

const handleOpenSession = async (row: LiveSessionSummary) => {
  try {
    const res = await getSnapshot(row.session_id)
    if (res.data.code === 200 && res.data.data) {
      snapshot.value = res.data.data
    }
  } catch {
    // 拦截器已提示
  }
}

onMounted(fetchSessions)
</script>

<style scoped>
.live-page {
  padding: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.card-id {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.summary-alert,
.input-card {
  margin-bottom: 12px;
}

.panel-card {
  margin-bottom: 12px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sentiment-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sentiment-detail {
  flex: 1;
}

.sentiment-score {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.sentiment-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.summary-text {
  font-size: 13px;
  margin: 8px 0 4px;
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.price-desc {
  margin-top: 10px;
}

.sparkline {
  width: 100%;
  height: 56px;
  margin-top: 10px;
  background: linear-gradient(180deg, rgba(59, 109, 240, 0.08), transparent);
  border-radius: 6px;
}
</style>
