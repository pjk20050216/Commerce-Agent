<template>
  <div class="buyer-page">
    <el-row :gutter="16">
      <el-col :span="9">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>虚拟买手团 · 候选商品</span>
              <el-tag size="small" type="info">三路 Agent 并行</el-tag>
            </div>
          </template>

          <el-form label-width="92px" size="default">
            <el-form-item label="用户 ID">
              <el-input v-model="form.userId" placeholder="用于关联历史偏好" />
            </el-form-item>
            <el-form-item label="商品标题">
              <el-input v-model="form.title" placeholder="如：极简风纯色棉质宽松衬衫" />
            </el-form-item>
            <el-form-item label="当前价格">
              <el-input-number v-model="form.price" :min="0" :precision="2" :step="10" />
            </el-form-item>
            <el-form-item label="类目">
              <el-input v-model="form.category" placeholder="如：女装" />
            </el-form-item>
            <el-form-item label="风格标签">
              <el-input v-model="form.tags" placeholder="逗号分隔，如：极简,纯色,棉" />
            </el-form-item>
            <el-form-item label="评价样本">
              <el-input
                v-model="form.reviews"
                type="textarea"
                :rows="4"
                placeholder="每行一条评价，用于差评关键词挖掘"
              />
            </el-form-item>
            <el-form-item label="退货率">
              <el-input-number
                v-model="form.returnRate"
                :min="0"
                :max="1"
                :step="0.01"
                :precision="2"
              />
              <span class="hint">0-1，留空表示未知</span>
            </el-form-item>
            <el-form-item label="历史行为">
              <el-input
                v-model="form.history"
                type="textarea"
                :rows="3"
                placeholder="每行：动作|标题|标签|价格，如 purchase|简约纯色T恤|极简,纯色|89"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleGenerate">
                生成决策卡
              </el-button>
              <el-button :loading="comparing" @click="handleCompare">仅比价</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <span>历史决策卡</span>
              <el-button size="small" text @click="fetchHistory">刷新</el-button>
            </div>
          </template>
          <el-table
            :data="history"
            size="small"
            v-loading="historyLoading"
            @row-click="handleOpenHistory"
          >
            <el-table-column prop="title" label="商品" show-overflow-tooltip />
            <el-table-column prop="overall_score" label="评分" width="70" />
            <el-table-column label="建议" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="REC_TYPE[row.recommendation as Recommendation]">
                  {{ REC_LABEL[row.recommendation as Recommendation] }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!historyLoading && history.length === 0" description="暂无记录" />
        </el-card>
      </el-col>

      <el-col :span="15">
        <el-card v-if="card" class="result-card">
          <template #header>
            <div class="card-header">
              <span>买手决策卡</span>
              <div class="header-right">
                <el-tag :type="REC_TYPE[card.recommendation]" effect="dark">
                  {{ REC_LABEL[card.recommendation] }}
                </el-tag>
                <span class="card-id">{{ card.card_id }}</span>
              </div>
            </div>
          </template>

          <el-alert
            v-if="card.is_mock_data"
            type="warning"
            :closable="false"
            show-icon
            title="比价数据来自模拟数据源，仅用于演示；接入 Elasticsearch 或采集服务后即为真实行情"
            class="mock-alert"
          />

          <!-- 综合评分 -->
          <div class="score-row">
            <el-progress
              type="dashboard"
              :percentage="Math.round(card.score.overall)"
              :width="130"
              :color="scoreColor"
            >
              <template #default>
                <div class="score-value">{{ card.score.overall.toFixed(1) }}</div>
                <div class="score-label">综合评分</div>
              </template>
            </el-progress>

            <div class="sub-scores">
              <div v-for="item in subScores" :key="item.key" class="sub-score">
                <span class="sub-label">{{ item.label }}</span>
                <el-progress
                  :percentage="Math.round(item.value)"
                  :stroke-width="10"
                  :color="scoreColor"
                />
                <span class="sub-weight">权重 {{ (item.weight * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>

          <el-alert
            :title="card.buy_advice"
            type="info"
            :closable="false"
            show-icon
            class="advice-alert"
          />

          <!-- 推荐理由 -->
          <el-divider content-position="left">推荐理由</el-divider>
          <ul class="reason-list">
            <li v-for="(reason, index) in card.reasons" :key="index">{{ reason }}</li>
          </ul>

          <!-- 风险预警 -->
          <el-divider content-position="left">风险预警（{{ card.warnings.length }}）</el-divider>
          <div v-if="card.warnings.length" class="warning-list">
            <el-alert
              v-for="(warning, index) in card.warnings"
              :key="index"
              :type="WARN_TYPE[warning.severity]"
              :closable="false"
              show-icon
              :title="`[${warning.kind}] ${warning.message}`"
            />
          </div>
          <el-empty v-else description="未发现明显风险" :image-size="60" />

          <el-row :gutter="12" class="detail-row">
            <el-col :span="12">
              <el-card shadow="never" class="inner-card">
                <template #header>全网比价</template>
                <el-descriptions :column="1" size="small" border>
                  <el-descriptions-item label="比价结论">
                    {{ PRICE_LABEL[card.price_comparison.verdict] }}
                  </el-descriptions-item>
                  <el-descriptions-item label="当前价">
                    {{ money(card.price_comparison.current_price) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="全网最低">
                    {{ money(card.price_comparison.lowest?.price ?? null) }}
                    <span v-if="card.price_comparison.lowest">
                      （{{ card.price_comparison.lowest.platform }}）
                    </span>
                  </el-descriptions-item>
                  <el-descriptions-item label="历史最低">
                    {{ money(card.price_comparison.historical_low) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="历史均价">
                    {{ money(card.price_comparison.historical_avg) }}
                  </el-descriptions-item>
                </el-descriptions>

                <svg class="sparkline" viewBox="0 0 100 32" preserveAspectRatio="none">
                  <polyline :points="sparkline" fill="none" stroke="#3b6df0" stroke-width="1" />
                </svg>
                <div class="sparkline-hint">
                  近 {{ card.price_comparison.history.length }} 天价格曲线（数据源：
                  {{ card.price_comparison.source }}）
                </div>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card shadow="never" class="inner-card">
                <template #header>风格画像</template>
                <div class="tag-row">
                  <el-tag
                    v-for="style in card.style_profile.dominant_styles"
                    :key="style.name"
                    size="small"
                    effect="plain"
                  >
                    {{ style.name }} {{ (style.weight * 100).toFixed(0) }}%
                  </el-tag>
                  <span v-if="!card.style_profile.dominant_styles.length" class="hint">
                    样本不足，暂未识别偏好
                  </span>
                </div>
                <p class="summary-text">{{ card.style_profile.summary }}</p>
                <p class="hint">
                  样本 {{ card.style_profile.based_on_records }} 条 · 置信度
                  {{ (card.style_profile.confidence * 100).toFixed(0) }}%
                </p>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never" class="inner-card quality-card">
            <template #header>
              质量口碑（{{ card.quality.score.toFixed(1) }} 分 ·
              {{ RISK_LABEL[card.quality.risk_level] }}）
            </template>
            <div class="tag-row">
              <el-tag
                v-for="defect in card.quality.insight.defect_keywords"
                :key="defect.keyword"
                size="small"
                type="danger"
                effect="plain"
              >
                {{ defect.keyword }} × {{ defect.count }}（{{ defect.category }}）
              </el-tag>
              <span v-if="!card.quality.insight.defect_keywords.length" class="hint">
                未发现集中缺陷
              </span>
            </div>
            <p class="summary-text">{{ card.quality.insight.summary }}</p>
            <el-table
              v-if="card.quality.insight.defect_keywords.length"
              :data="card.quality.insight.defect_keywords"
              size="small"
            >
              <el-table-column prop="keyword" label="关键词" width="110" />
              <el-table-column prop="category" label="类型" width="90" />
              <el-table-column prop="count" label="次数" width="70" />
              <el-table-column label="严重度" width="120">
                <template #default="{ row }">
                  <el-progress :percentage="Math.round(row.severity * 100)" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column label="原文片段" show-overflow-tooltip>
                <template #default="{ row }">{{ row.quotes.join(' / ') }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-collapse class="trace-collapse">
            <el-collapse-item :title="`Agent 执行痕迹（${card.agent_trace.length}）`">
              <el-timeline>
                <el-timeline-item
                  v-for="trace in card.agent_trace"
                  :key="trace.agent"
                  :timestamp="trace.status"
                  :type="trace.status === 'completed' ? 'success' : 'warning'"
                >
                  {{ trace.agent }}：{{ trace.detail }}
                </el-timeline-item>
              </el-timeline>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <el-card v-else>
          <el-empty description="填写左侧商品信息，让买手团给出决策" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { comparePrice, createDecision, getDecision, listDecisions } from '@/api/buyer'
import type {
  BrowsingAction,
  BrowsingRecord,
  BuyerDecisionCard,
  BuyerDecisionSummary,
  PriceVerdict,
  Recommendation,
  RiskLevel,
} from '@/types/buyer'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

const REC_LABEL: Record<Recommendation, string> = {
  strong_buy: '强烈推荐',
  buy: '推荐购买',
  consider: '谨慎考虑',
  avoid: '暂不推荐',
}

const REC_TYPE: Record<Recommendation, TagType> = {
  strong_buy: 'success',
  buy: 'success',
  consider: 'warning',
  avoid: 'danger',
}

const PRICE_LABEL: Record<PriceVerdict, string> = {
  great_deal: '处于低位，值得买',
  fair: '价格合理',
  wait: '建议再等等',
  overpriced: '溢价明显',
}

const RISK_LABEL: Record<RiskLevel, string> = {
  low: '风险低',
  medium: '风险中',
  high: '风险高',
}

type AlertType = 'success' | 'warning' | 'info' | 'error'

const WARN_TYPE: Record<RiskLevel, AlertType> = {
  low: 'info',
  medium: 'warning',
  high: 'error',
}

const loading = ref(false)
const comparing = ref(false)
const historyLoading = ref(false)
const card = ref<BuyerDecisionCard | null>(null)
const history = ref<BuyerDecisionSummary[]>([])

const form = reactive({
  userId: 'u1001',
  title: '极简风纯色棉质宽松衬衫',
  price: 199,
  category: '女装',
  tags: '极简,纯色,棉',
  reviews: '掉色严重\n尺码偏小\n面料起球\n版型不错',
  returnRate: 0.23 as number | undefined,
  history: 'purchase|简约纯色T恤|极简,纯色|89\ncart|基础款衬衫|极简|159',
})

const subScores = computed(() => {
  if (!card.value) return []
  const weights = card.value.score.weights
  return [
    { key: 'style', label: '风格匹配', value: card.value.score.style_fit, weight: weights.style },
    { key: 'value', label: '性价比', value: card.value.score.value_score, weight: weights.value },
    {
      key: 'quality',
      label: '质量口碑',
      value: card.value.score.quality_score,
      weight: weights.quality,
    },
  ]
})

const scoreColor = computed(() => {
  const score = card.value?.score.overall ?? 0
  if (score >= 85) return '#10b981'
  if (score >= 72) return '#3b6df0'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
})

const sparkline = computed(() => {
  const points = card.value?.price_comparison.history ?? []
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

const money = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : `¥${value.toFixed(2)}`

const splitList = (value: string): string[] =>
  value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean)

/** 把「动作|标题|标签|价格」多行文本解析为浏览记录 */
const parseHistory = (value: string): BrowsingRecord[] => {
  const actions: BrowsingAction[] = ['view', 'favorite', 'cart', 'purchase']
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [action, title, tags, price] = line.split('|')
      const parsedAction = actions.includes(action as BrowsingAction)
        ? (action as BrowsingAction)
        : 'view'
      return {
        item_id: `manual-${index}`,
        title: (title || line).trim(),
        tags: tags ? splitList(tags) : [],
        price: price ? Number(price) : null,
        action: parsedAction,
      } as BrowsingRecord
    })
}

const buildPayload = () => ({
  user_id: form.userId,
  candidate: {
    title: form.title,
    price: form.price,
    category: form.category || null,
    tags: splitList(form.tags),
    reviews: form.reviews
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean),
    return_rate: form.returnRate ?? null,
  },
  history: parseHistory(form.history),
})

const handleGenerate = async () => {
  if (!form.userId || !form.title) {
    ElMessage.warning('请填写用户 ID 与商品标题')
    return
  }
  loading.value = true
  try {
    const res = await createDecision(buildPayload())
    if (res.data.code === 200 && res.data.data) {
      card.value = res.data.data
      ElMessage.success('决策卡已生成')
      fetchHistory()
    } else {
      ElMessage.error(res.data.message || '生成失败')
    }
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

const handleCompare = async () => {
  if (!form.title) {
    ElMessage.warning('请先填写商品标题')
    return
  }
  comparing.value = true
  try {
    const res = await comparePrice({ title: form.title, current_price: form.price })
    if (res.data.code === 200 && res.data.data) {
      ElMessage.success(`比价完成：${PRICE_LABEL[res.data.data.verdict]}`)
    }
  } finally {
    comparing.value = false
  }
}

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const res = await listDecisions({ limit: 10 })
    if (res.data.code === 200 && Array.isArray(res.data.data)) {
      history.value = res.data.data
    }
  } finally {
    historyLoading.value = false
  }
}

const handleOpenHistory = async (row: BuyerDecisionSummary) => {
  try {
    const res = await getDecision(row.card_id)
    if (res.data.code === 200 && res.data.data) {
      card.value = res.data.data
    }
  } catch {
    // 拦截器已提示
  }
}

onMounted(fetchHistory)
</script>

<style scoped>
.buyer-page {
  padding: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-id {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.history-card {
  margin-top: 16px;
}

.mock-alert,
.advice-alert {
  margin-bottom: 16px;
}

.score-row {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 8px 0 16px;
}

.score-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.score-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.sub-scores {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sub-score {
  display: grid;
  grid-template-columns: 72px 1fr 80px;
  align-items: center;
  gap: 10px;
}

.sub-label {
  font-size: 13px;
}

.sub-weight {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.reason-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.9;
  font-size: 13px;
}

.warning-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-row {
  margin-top: 16px;
}

.inner-card {
  margin-bottom: 12px;
}

.quality-card {
  margin-top: 4px;
}

.sparkline {
  width: 100%;
  height: 60px;
  margin-top: 12px;
  background: linear-gradient(180deg, rgba(59, 109, 240, 0.08), transparent);
  border-radius: 6px;
}

.sparkline-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.summary-text {
  font-size: 13px;
  line-height: 1.7;
  margin: 4px 0;
}

.hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.trace-collapse {
  margin-top: 12px;
}
</style>
