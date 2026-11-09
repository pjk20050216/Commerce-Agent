<template>
  <div class="knowledge-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识库文档</span>
          <div>
            <el-button size="small" @click="fetchStats">刷新统计</el-button>
            <el-button size="small" type="primary" @click="showUpload = true">上传文档</el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="12" class="stats-row">
        <el-col :span="8">
          <el-statistic title="文档总数" :value="stats.total_documents" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="分块总数" :value="stats.total_chunks" />
        </el-col>
        <el-col :span="8">
          <div class="type-tags">
            <el-tag
              v-for="(count, type) in stats.documents_by_type"
              :key="type"
              size="small"
              effect="plain"
            >
              {{ DOC_TYPE_LABELS[type as DocType] || type }} {{ count }}
            </el-tag>
          </div>
        </el-col>
      </el-row>

      <el-form :inline="true" class="filter-row">
        <el-form-item label="类型">
          <el-select v-model="filters.docType" placeholder="全部" clearable style="width: 150px">
            <el-option
              v-for="(label, value) in DOC_TYPE_LABELS"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchDocuments">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="documents" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ DOC_TYPE_LABELS[row.doc_type as DocType] || row.doc_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类目" width="120" />
        <el-table-column prop="source" label="来源" width="160" show-overflow-tooltip />
        <el-table-column prop="version" label="版本" width="70" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button size="small" type="danger" text @click="handleDelete(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && documents.length === 0" description="暂无文档" />
    </el-card>

    <el-dialog v-model="showUpload" title="上传知识文档" width="480px">
      <el-form label-width="80px">
        <el-form-item label="文件">
          <input type="file" accept=".txt,.md,.pdf,.docx" @change="handleFileChange" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="uploadForm.docType" style="width: 100%">
            <el-option
              v-for="(label, value) in DOC_TYPE_LABELS"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="类目">
          <el-input v-model="uploadForm.category" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteDocument,
  getDocuments,
  getKnowledgeStats,
  uploadDocument,
} from '@/api/knowledge'
import { DOC_TYPE_LABELS } from '@/types/knowledge'
import type { DocType, KnowledgeDocument, KnowledgeStats } from '@/types/knowledge'

const loading = ref(false)
const uploading = ref(false)
const showUpload = ref(false)
const documents = ref<KnowledgeDocument[]>([])
const stats = ref<KnowledgeStats>({
  total_documents: 0,
  total_chunks: 0,
  documents_by_type: {},
})
const filters = reactive<{ docType?: DocType }>({})
const uploadForm = reactive<{ docType: DocType; category: string; file: File | null }>({
  docType: 'category_knowledge',
  category: '',
  file: null,
})

const formatTime = (value: string): string => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

const fetchDocuments = async () => {
  loading.value = true
  try {
    const res = await getDocuments({ doc_type: filters.docType, page: 1, page_size: 50 })
    if (res.data.code === 200 && res.data.data) {
      documents.value = res.data.data.documents
    }
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  const res = await getKnowledgeStats()
  if (res.data.code === 200 && res.data.data) {
    stats.value = res.data.data
  }
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  uploadForm.file = target.files?.[0] ?? null
}

const handleUpload = async () => {
  if (!uploadForm.file) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    const res = await uploadDocument(
      uploadForm.file,
      uploadForm.docType,
      uploadForm.category || undefined
    )
    if (res.data.code === 200) {
      ElMessage.success('上传成功')
      showUpload.value = false
      uploadForm.file = null
      fetchDocuments()
      fetchStats()
    } else {
      ElMessage.error(res.data.message || '上传失败')
    }
  } finally {
    uploading.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除该文档？', '提示')
  } catch {
    return
  }
  const res = await deleteDocument(id)
  if (res.data.code === 200) {
    ElMessage.success('已删除')
    fetchDocuments()
    fetchStats()
  }
}

onMounted(() => {
  fetchDocuments()
  fetchStats()
})
</script>

<style scoped>
.knowledge-page {
  padding: 4px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.stats-row {
  margin-bottom: 16px;
}

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 6px;
}

.filter-row {
  margin-bottom: 8px;
}
</style>
