<template>
  <div class="dispute-page">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>仲裁庭 · 案件材料</span>
              <el-tag size="small" type="info">事实 → 规则 → 话术</el-tag>
            </div>
          </template>

          <el-form label-width="76px" size="default">
            <el-form-item label="订单号">
              <el-input v-model="form.orderId" placeholder="如 ORD20261109001" />
            </el-form-item>
            <el-form-item label="平台">
              <el-input v-model="form.platform" placeholder="淘宝 / 京东 / 抖音" />
            </el-form-item>
            <el-form-item label="金额">
              <el-input-number v-model="form.amount" :min="0" :precision="2" :step="10" />
            </el-form-item>
            <el-form-item label="商品">
              <el-input v-model="form.productTitle" placeholder="商品标题" />
            </el-form-item>
            <el-form-item label="签收时间">
              <el-date-picker
                v-model="form.receivedAt"
                type="datetime"
                placeholder="选择签收时间"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="我的诉求">
              <el-input
                v-model="form.claim"
                type="textarea"
                :rows="2"
                placeholder="如：要求退货退款"
              />
            </el-form-item>
            <el-form-item label="聊天记录">
              <el-input
                v-model="form.chat"
                type="textarea"
                :rows="4"
                placeholder="每行：角色|内容，角色取 consumer/merchant/platform"
              />
            </el-form-item>
            <el-form-item label="物流轨迹">
              <el-input
                v-model="form.logistics"
                type="textarea"
                :rows="2"
                placeholder="每行：状态|描述，如 已签收|本人签收"
              />
            </el-form-item>
            <el-form-item label="开箱凭证">
              <el-input
                v-model="form.unboxing"
                type="textarea"
                :rows="2"
                placeholder="每行：图片地址|描述"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleSubmit">
                生成裁决与话术
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card v-if="result" class="result-card">
          <template #header>
            <div class="card-header">
              <span>裁决结果</span>
              <div class="header-right">
                <el-tag :type="RESP_TYPE[result.verdict.responsibility]" effect="dark">
                  {{ RESP_LABEL[result.verdict.responsibility] }}
                </el-tag>
                <span class="card-id">置信度 {{ (result.verdict.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </template>

          <el-alert
            :title="result.verdict.reasoning"
            :type="RESP_TYPE[result.verdict.responsibility] === 'success' ? 'success' : 'warning'"
            :closable="false"
            show-icon
            class="reasoning-alert"
          />

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="案件编号">
              {{ result.case_id }}
            </el-descriptions-item>
            <el-descriptions-item label="诉求类型">
              {{ CLAIM_LABEL[result.verdict.claim] }}
            </el-descriptions-item>
            <el-descriptions-item label="建议方案" :span="2">
              {{ result.verdict.suggested_compensation }}
            </el-descriptions-item>
            <el-descriptions-item label="时效提示" :span="2">
              {{ result.verdict.deadline_advice }}
            </el-descriptions-item>
            <el-descriptions-item label="事实摘要" :span="2">
              {{ result.fact_sheet.summary }}
            </el-descriptions-item>
          </el-descriptions>

          <el-row :gutter="12" class="detail-row">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>命中规则（{{ result.verdict.matched_rules.length }}）</template>
                <el-table :data="result.verdict.matched_rules" size="small">
                  <el-table-column prop="rule_id" label="编号" width="110" />
                  <el-table-column prop="name" label="规则" show-overflow-tooltip />
                  <el-table-column prop="category" label="类别" width="80" />
                  <el-table-column label="权重" width="80">
                    <template #default="{ row }">{{ row.weight.toFixed(2) }}</template>
                  </el-table-column>
                </el-table>

                <el-divider content-position="left">引用条款</el-divider>
                <ul class="clause-list">
                  <li v-for="(clause, index) in result.verdict.legal_basis" :key="index">
                    {{ clause }}
                  </li>
                </ul>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card shadow="never">
                <template #header>事实时间线</template>
                <el-timeline>
                  <el-timeline-item
                    v-for="(node, index) in result.fact_sheet.timeline"
                    :key="index"
                    :timestamp="formatTime(node.occurred_at)"
                    placement="top"
                  >
                    <strong>[{{ node.phase }}] {{ node.title }}</strong>
                    <div class="timeline-detail">{{ node.detail }}</div>
                  </el-timeline-item>
                </el-timeline>
                <el-empty
                  v-if="!result.fact_sheet.timeline.length"
                  description="暂无时间线"
                  :image-size="60"
                />
              </el-card>
            </el-col>
          </el-row>

          <el-card v-if="result.fact_sheet.evidence_gaps.length" shadow="never" class="gap-card">
            <template #header>证据缺口（{{ result.fact_sheet.evidence_gaps.length }}）</template>
            <el-alert
              v-for="(gap, index) in result.fact_sheet.evidence_gaps"
              :key="index"
              :title="gap"
              type="warning"
              :closable="false"
              show-icon
              class="gap-alert"
            />
          </el-card>

          <el-card shadow="never" class="draft-card">
            <template #header>
              <div class="card-header">
                <span>维权话术</span>
                <el-button size="small" @click="handleRegenerate">重新生成当前语气</el-button>
              </div>
            </template>

            <el-tabs v-model="activeTone">
              <el-tab-pane
                v-for="draft in result.drafts"
                :key="draft.tone"
                :label="TONE_LABEL[draft.tone]"
                :name="draft.tone"
              >
                <div class="draft-header">
                  <strong>{{ draft.title }}</strong>
                  <el-button size="small" type="primary" plain @click="handleCopy(draft.body)">
                    复制正文
                  </el-button>
                </div>
                <pre class="draft-body">{{ draft.body }}</pre>
                <el-divider content-position="left">后续动作建议</el-divider>
                <ul class="clause-list">
                  <li v-for="(action, index) in draft.next_actions" :key="index">{{ action }}</li>
                </ul>
              </el-tab-pane>
            </el-tabs>
          </el-card>

          <p class="disclaimer">{{ result.disclaimer }}</p>
        </el-card>

        <el-card v-else>
          <el-empty description="填写左侧案件材料，仲裁庭会给出责任判定与三套话术" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { createCase, regenerateDraft } from '@/api/dispute'
import type {
  ChatMessageInput,
  ComplaintDraft,
  DisputeCaseResult,
  DisputeClaim,
  DraftTone,
  LogisticsEventInput,
  Responsibility,
  Speaker,
  UnboxingEvidence,
} from '@/types/dispute'

type TagType = 'primary' | 'success' | 'info' | 'warning' | 'danger'

const RESP_LABEL: Record<Responsibility, string> = {
  merchant: '商家责任',
  consumer: '消费者举证不足',
  platform: '平台责任',
  shared: '双方共担',
  undetermined: '责任待定',
}

const RESP_TYPE: Record<Responsibility, TagType> = {
  merchant: 'danger',
  consumer: 'warning',
  platform: 'warning',
  shared: 'info',
  undetermined: 'info',
}

const CLAIM_LABEL: Record<DisputeClaim, string> = {
  refund_only: '仅退款',
  refund_with_return: '退货退款',
  return_repair: '维修 / 补发',
  exchange: '换货',
  compensation: '索赔',
  apology: '赔礼道歉',
  undetermined: '未明确',
}

const TONE_LABEL: Record<DraftTone, string> = {
  complaint: '投诉',
  appeal: '申诉',
  negotiation: '协商',
}

const loading = ref(false)
const result = ref<DisputeCaseResult | null>(null)
const activeTone = ref<DraftTone>('complaint')

const form = reactive({
  orderId: 'ORD20261109001',
  platform: '淘宝',
  amount: 199,
  productTitle: '纯棉衬衫',
  receivedAt: new Date(Date.now() - 3 * 24 * 3600 * 1000),
  claim: '衣服洗了一次掉色严重，要求退货退款',
  chat: 'consumer|衣服洗了一次就掉色严重，要求退货退款\nmerchant|已经拆封使用过了，我们拒绝退款',
  logistics: '已签收|快件已签收，签收人：本人',
  unboxing: 'https://example.invalid/u1.jpg|开箱实拍，领口处有明显掉色痕迹',
})

const splitLines = (value: string): string[] =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

/** 解析「角色|内容」格式的聊天记录 */
const parseChat = (value: string): ChatMessageInput[] => {
  const speakers: Speaker[] = ['consumer', 'merchant', 'platform', 'system']
  return splitLines(value).map((line) => {
    const [speaker, ...rest] = line.split('|')
    const content = rest.join('|').trim() || line
    const parsed = speakers.includes(speaker as Speaker) ? (speaker as Speaker) : 'consumer'
    return { speaker: parsed, content }
  })
}

/** 解析「状态|描述」格式的物流轨迹 */
const parseLogistics = (value: string): LogisticsEventInput[] =>
  splitLines(value).map((line) => {
    const [status, ...rest] = line.split('|')
    return { status: status.trim() || '已签收', description: rest.join('|').trim() || null }
  })

/** 解析「地址|描述」格式的开箱凭证 */
const parseUnboxing = (value: string): UnboxingEvidence[] =>
  splitLines(value).map((line) => {
    const [url, ...rest] = line.split('|')
    return { image_url: url.trim(), description: rest.join('|').trim() }
  })

const formatTime = (value: string | null): string => {
  if (!value) return '时间未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

const handleSubmit = async () => {
  if (!form.orderId || !form.platform) {
    ElMessage.warning('请填写订单号与平台')
    return
  }
  loading.value = true
  try {
    const res = await createCase({
      order: {
        order_id: form.orderId,
        platform: form.platform,
        amount: form.amount,
        product_title: form.productTitle,
        received_at: form.receivedAt ? form.receivedAt.toISOString() : null,
      },
      claim_text: form.claim,
      chat_log: parseChat(form.chat),
      logistics: parseLogistics(form.logistics),
      unboxing: parseUnboxing(form.unboxing),
    })
    if (res.data.code === 200 && res.data.data) {
      result.value = res.data.data
      activeTone.value = 'complaint'
      ElMessage.success('裁决已生成')
    } else {
      ElMessage.error(res.data.message || '仲裁失败')
    }
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

const handleRegenerate = async () => {
  if (!result.value) return
  const draft = await regenerateDraft(result.value.case_id, activeTone.value)
  const updated: ComplaintDraft | undefined = draft.data.data
  if (updated) {
    result.value.drafts = result.value.drafts.map((item) =>
      item.tone === updated.tone ? updated : item
    )
    ElMessage.success('已重新生成')
  }
}

const handleCopy = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}
</script>

<style scoped>
.dispute-page {
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

.reasoning-alert {
  margin-bottom: 16px;
}

.detail-row {
  margin-top: 12px;
}

.gap-card,
.draft-card {
  margin-top: 12px;
}

.gap-alert {
  margin-bottom: 8px;
}

.clause-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.8;
}

.timeline-detail {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.draft-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.draft-body {
  margin: 0;
  padding: 14px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.disclaimer {
  margin: 16px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
