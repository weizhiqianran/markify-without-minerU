import streamlit as st
import requests
import time
import os

# ============ 配置区 ============
BASE_URL = "http://localhost:20926"


# ============ 工具函数 ============

def fetch_jobs(page=0, limit=10):
    """
    从后端 /api/jobs 获取最新任务列表
    （请确保后端已实现 ?page=...&limit=... 分页参数）
    """
    url = f"{BASE_URL}/api/jobs?page={page}&limit={limit}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()  # 后端应返回一个任务列表 (list)
        else:
            st.error(f"获取任务列表失败: {resp.text}")
            return []
    except requests.RequestException as e:
        st.error(f"网络异常: {e}")
        return []


def upload_file(file, mode):
    """
    上传单个文件到后端，创建任务。
    成功后立刻刷新页面，以获取最新的任务列表。
    """
    files = {"file": file}
    data = {"mode": mode}
    try:
        response = requests.post(f"{BASE_URL}/api/jobs", files=files, data=data)
        if response.status_code == 202:
            st.success(f"文件 `{file.name}` 上传成功，已加入任务队列。")
            st.rerun()  # 替换为 st.rerun()
        else:
            st.error(f"文件 `{file.name}` 上传失败: {response.text}")
    except requests.RequestException as e:
        st.error(f"网络异常：{e}")


def upload_url(url, mode):
    """
    上传单个 URL 到后端，创建任务。
    成功后立刻刷新页面，以获取最新的任务列表。
    """
    data = {"url": url, "mode": mode}
    try:
        response = requests.post(f"{BASE_URL}/api/jobs/url", json=data)
        if response.status_code == 202:
            st.success(f"URL `{url}` 提交成功，已加入任务队列。")
            st.rerun()  # 替换为 st.rerun()
        else:
            st.error(f"URL `{url}` 上传失败: {response.text}")
    except requests.RequestException as e:
        st.error(f"网络异常：{e}")


def show_file_entry(job):
    """
    在右侧文件列表中渲染每个任务条目。
    后端返回的 job 数据结构示例（JSON）:
      {
        "job_id": "xxx",
        "status": "completed",
        "filename": "test.pdf",
        "params": {"mode": "simple"},
        "error": null,
        "created_at": "2025-02-25T10:00:00"
      }
    你也可以根据后端的返回字段进行修改。
    """
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

    with col1:
        st.markdown(f"**{job['filename']}**")

    # 如果后端返回了 created_at，可显示
    with col2:
        created_time = job.get("created_at", "")
        st.markdown(f"{created_time}")

    with col3:
        status = job["status"]
        if status == "completed":
            status_icon = "✅"
        elif status == "failed":
            status_icon = "❌"
        else:
            status_icon = "⏳"
        st.markdown(f"{status_icon} {status}")

    with col4:
        # 如果已完成，提供下载
        if status == "completed":
            try:
                result_response = requests.get(f"{BASE_URL}/api/jobs/{job['job_id']}/result")
                if result_response.status_code == 200:
                    st.download_button(
                        label="下载",
                        data=result_response.content,
                        file_name=f"{job['filename']}.md",
                        mime="text/markdown",
                        key=f"download_{job['job_id']}"  # 添加唯一 key
                    )
                else:
                    st.error("无法下载")
            except requests.RequestException as e:
                st.error(f"下载异常：{e}")


# ============ 主函数 ============

def main():
    st.set_page_config(page_title="Markify", layout="wide")

    # 页面标题与说明
    st.title("Markify - 文档处理")
    st.markdown("在左侧上传文件或提交 URL，右侧实时查看进度并下载结果。")

    # 布局：左侧上传，右侧列表
    left_col, right_col = st.columns([2, 3], gap="large")

    with left_col:
        st.subheader("上传设置")
        mode = st.selectbox("选择 PDF 处理模式", ["simple", "advanced", "cloud"])

        # 本地文件上传
        uploaded_files = st.file_uploader(
            "选择文件（任意类型）",
            type=None,
            accept_multiple_files=True
        )
        if uploaded_files and st.button("上传文件"):
            for file in uploaded_files:
                upload_file(file, mode)

        # URL 上传
        st.subheader("URL 上传")
        file_urls = st.text_area("请输入文件 URL（每行一个）")
        if file_urls and st.button("提交 URL"):
            for url in file_urls.strip().split("\n"):
                if url:
                    upload_url(url.strip(), mode)

        # 结果存储位置（移除 MinerU 引用）
        st.markdown(f"**解析结果存储路径**：`{os.path.expanduser('~')}/Markify`")

    with right_col:
        st.subheader("文件列表")

        # 手动刷新按钮
        if st.button("刷新列表"):
            st.rerun()  # 替换为 st.rerun()

        # 从后端获取任务列表
        jobs = fetch_jobs(page=0, limit=10)
        if not jobs:
            st.info("暂无任务，请上传后查看。")
        else:
            for job in jobs:
                show_file_entry(job)


if __name__ == "__main__":
    main()