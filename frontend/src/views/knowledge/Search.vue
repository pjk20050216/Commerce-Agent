<template>
  <div class="knowledge-search">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>检索测试</span>
          <span class="hint">验证 RAG 召回效果（需启用 RAG_ENABLED）</span>
        </div>
      </template>

      <el-form :inline="true">
        <el-form-item label="查询">
          <el-input
            v-model="form.query"
            placeholder="如：主图白底要求"
            style="width: 320px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.docType" placeholder="全部" clearable style="width: 140px">
            <el-option
              v-for="(label, value) in DOC_TYPE_LABELS"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="TopK">
          <el-input-number v-model="form.topK" :min="1" :max="20" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">检索</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!results.length && !loading" description="输入查询语句开始检索" />

      <div v-for="item in results" :key="item.chunk_id" class="result-item">
        <div class="result-header">
          <span class="doc-title">{{ item.doc_title }}</span>
          <el-tag size="small" effect="plain">
            {{ DOC_TYPE_LABELS[item.doc_type] || item.doc_type }}
          </el-tag>
          <el-progress
            :percentage="Math.round(item.similarity * 100)"
            :stroke-width="8"
            style="width: 140px"
          />
        </div>
        <p class="result-content">{{ item.content }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { searchKnowledge } from '@/api/knowledge'
import { DOC_TYPE_LABELS } from '@/types/knowledge'
import type { DocType, SearchResultItem } from '@/types/knowledge'

const loading = ref(false)
const results = ref<SearchResultItem[]>([])
const form = reactive<{ query: string; docType?: DocType; topK: number }>({
  query: '',
  topK: 5,
})

const handleSearch = async () => {
  if (!form.query.trim()) {
    ElMessage.warning('请输入查询语句')
    return
  }
  loading.value = true
  try {
    const res = await searchKnowledge({
      query: form.query,
      doc_type: form.docType,
      top_k: form.topK,
    })
    if (res.data.code === 200 && res.data.data) {
      results.value = res.data.data.results
      if (!results.value.length) {
        ElMessage.info('没有召回结果，可能是知识库为空或未启用 RAG')
      }
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.knowledge-search {
  padding: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.result-item {
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.doc-title {
  font-weight: 600;
  font-size: 13px;
}

.result-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
}
</style>
