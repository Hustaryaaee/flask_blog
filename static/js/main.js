/* =====================================================================
   博客前端脚本 (main.js)
   ---------------------------------------------------------------------
   功能模块:
   1. 表单验证(Bootstrap 5 自定义验证)
   2. 删除确认
   3. Flash 消息自动消失
   4. 工具提示(Tooltip)初始化
   5. 平滑滚动与返回顶部
   6. 通用工具函数
   ===================================================================== */

(function () {
    'use strict';

    /* ============================================================
       工具函数
       ============================================================ */
    const BlogUtils = {
        /**
         * DOM 就绪回调
         * @param {Function} fn - 要执行的函数
         */
        ready: function (fn) {
            if (document.readyState !== 'loading') {
                fn();
            } else {
                document.addEventListener('DOMContentLoaded', fn);
            }
        },

        /**
         * 防抖函数
         * @param {Function} func - 目标函数
         * @param {number} wait - 等待毫秒
         */
        debounce: function (func, wait) {
            let timeout;
            return function () {
                const context = this;
                const args = arguments;
                clearTimeout(timeout);
                timeout = setTimeout(function () {
                    func.apply(context, args);
                }, wait);
            };
        },

        /**
         * HTML 转义
         * @param {string} str - 原始字符串
         * @returns {string} 转义后字符串
         */
        escapeHtml: function (str) {
            if (str === null || str === undefined) return '';
            const div = document.createElement('div');
            div.textContent = String(str);
            return div.innerHTML;
        }
    };

    /* ============================================================
       模块 1: Bootstrap 表单验证
       ============================================================ */
    const FormValidator = {
        init: function () {
            // 获取所有带 needs-validation 类的表单
            const forms = document.querySelectorAll('.needs-validation');
            if (!forms.length) return;

            Array.from(forms).forEach(function (form) {
                form.addEventListener('submit', function (event) {
                    event.preventDefault();
                    event.stopPropagation();

                    if (form.checkValidity()) {
                        FormValidator.onValidSubmit(form);
                    } else {
                        FormValidator.onInvalidSubmit(form);
                    }

                    form.classList.add('was-validated');
                }, false);

                // 实时验证:输入时清除错误状态
                form.querySelectorAll('input, textarea, select').forEach(function (input) {
                    input.addEventListener('input', function () {
                        if (input.checkValidity()) {
                            input.classList.remove('is-invalid');
                            input.classList.add('is-valid');
                        } else {
                            input.classList.remove('is-valid');
                        }
                    });
                });
            });
        },

        /**
         * 表单验证通过
         */
        onValidSubmit: function (form) {
            // 防止重复提交
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalHtml = submitBtn.innerHTML;
                submitBtn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>提交中...';

                // 10 秒后恢复(防止网络异常时按钮永久禁用)
                setTimeout(function () {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHtml;
                }, 10000);
            }
            // 真正提交表单
            form.submit();
        },

        /**
         * 表单验证失败
         */
        onInvalidSubmit: function (form) {
            // 滚动到第一个错误字段
            const firstInvalid = form.querySelector(':invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                setTimeout(function () { firstInvalid.focus(); }, 300);
            }
        }
    };


    /* ============================================================
       模块 2: 删除确认(兼容 Bootstrap Modal 与原生 confirm)
       ============================================================ */
    const DeleteConfirm = {
        init: function () {
            // 处理所有 data-confirm 属性的元素
            document.querySelectorAll('[data-confirm]').forEach(function (el) {
                el.addEventListener('click', function (e) {
                    const message = el.getAttribute('data-confirm') || '确定要执行此操作吗?';
                    if (!window.confirm(message)) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                });
            });

            // 处理文章详情页的删除模态框(由 post.html 内联脚本处理)
            const deleteModal = document.getElementById('deleteModal');
            if (deleteModal) {
                DeleteConfirm.bindModal(deleteModal);
            }
        },

        bindModal: function (modalEl) {
            modalEl.addEventListener('show.bs.modal', function (event) {
                const trigger = event.relatedTarget;
                if (!trigger) return;
                const title = trigger.getAttribute('data-post-title') || '该文章';
                const titleEl = modalEl.querySelector('[data-modal-title]');
                if (titleEl) {
                    titleEl.textContent = title;
                }
            });
        }
    };


    /* ============================================================
       模块 3: Flash 消息自动消失
       ============================================================ */
    const FlashMessages = {
        init: function () {
            const messages = document.querySelectorAll('.flash-message');
            if (!messages.length) return;

            messages.forEach(function (msg) {
                // 5 秒后开始淡出
                setTimeout(function () {
                    msg.classList.remove('show');
                    msg.classList.add('fade');
                    setTimeout(function () {
                        if (msg.parentNode) {
                            msg.parentNode.removeChild(msg);
                        }
                    }, 500);
                }, 5000);
            });
        }
    };


    /* ============================================================
       模块 4: Bootstrap 工具提示(Tooltip)初始化
       ============================================================ */
    const Tooltips = {
        init: function () {
            // 检查 Bootstrap 是否已加载
            if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) {
                return;
            }
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.forEach(function (el) {
                new bootstrap.Tooltip(el);
            });
        }
    };


    /* ============================================================
       模块 5: 字符计数器(为表单字段添加实时字符计数)
       ============================================================ */
    const CharCounter = {
        init: function () {
            document.querySelectorAll('[data-max-length]').forEach(function (el) {
                const max = parseInt(el.getAttribute('data-max-length'), 10);
                if (isNaN(max)) return;

                const counterEl = el.parentElement.querySelector('.char-counter');
                if (!counterEl) return;

                const update = BlogUtils.debounce(function () {
                    const len = el.value.length;
                    counterEl.textContent = len + ' / ' + max;
                    if (len > max) {
                        counterEl.classList.add('text-danger');
                        el.classList.add('is-invalid');
                    } else {
                        counterEl.classList.remove('text-danger');
                        el.classList.remove('is-invalid');
                    }
                }, 100);

                el.addEventListener('input', update);
                update(); // 初始
            });
        }
    };


    /* ============================================================
       模块 6: 离开页面前提示(对未保存的编辑表单)
       ============================================================ */
    const LeaveGuard = {
        init: function () {
            const form = document.querySelector('[data-leave-guard="true"]');
            if (!form) return;

            let dirty = false;
            const initialData = new FormData(form);

            // 检测字段变化
            form.addEventListener('input', function () {
                dirty = true;
            });
            form.addEventListener('submit', function () {
                dirty = false;
            });

            window.addEventListener('beforeunload', function (e) {
                if (dirty) {
                    e.preventDefault();
                    e.returnValue = '您有未保存的修改,确定要离开吗?';
                    return e.returnValue;
                }
            });
        }
    };


    /* ============================================================
       模块 7: 返回顶部按钮
       ============================================================ */
    const BackToTop = {
        init: function () {
            // 若页面没有 #backToTop 元素则创建
            let btn = document.getElementById('backToTop');
            if (!btn) {
                btn = document.createElement('button');
                btn.id = 'backToTop';
                btn.className = 'btn btn-primary btn-back-to-top';
                btn.setAttribute('aria-label', '返回顶部');
                btn.innerHTML = '<i class="bi bi-arrow-up"></i>';
                document.body.appendChild(btn);
            }

            const toggleVisibility = BlogUtils.debounce(function () {
                if (window.scrollY > 300) {
                    btn.classList.add('show');
                } else {
                    btn.classList.remove('show');
                }
            }, 100);

            window.addEventListener('scroll', toggleVisibility);
            btn.addEventListener('click', function () {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    };


    /* ============================================================
       模块 8: 文章搜索过滤(纯前端过滤,可选增强)
       ============================================================ */
    const PostFilter = {
        init: function () {
            const searchInput = document.getElementById('postSearch');
            const postCards = document.querySelectorAll('.post-card');
            if (!searchInput || !postCards.length) return;

            const doFilter = BlogUtils.debounce(function () {
                const query = searchInput.value.trim().toLowerCase();
                let visibleCount = 0;

                postCards.forEach(function (card) {
                    const titleEl = card.querySelector('.card-title');
                    const excerptEl = card.querySelector('.post-excerpt');
                    const title = titleEl ? titleEl.textContent.toLowerCase() : '';
                    const excerpt = excerptEl ? excerptEl.textContent.toLowerCase() : '';

                    if (!query || title.indexOf(query) !== -1 || excerpt.indexOf(query) !== -1) {
                        card.style.display = '';
                        visibleCount++;
                    } else {
                        card.style.display = 'none';
                    }
                });

                // 显示空结果提示
                const emptyEl = document.getElementById('searchEmpty');
                if (emptyEl) {
                    emptyEl.style.display = visibleCount === 0 ? '' : 'none';
                }
            }, 200);

            searchInput.addEventListener('input', doFilter);
        }
    };


    /* ============================================================
       初始化入口
       ============================================================ */
    BlogUtils.ready(function () {
        FormValidator.init();
        DeleteConfirm.init();
        FlashMessages.init();
        Tooltips.init();
        CharCounter.init();
        LeaveGuard.init();
        BackToTop.init();
        PostFilter.init();

        // 控制台标识
        if (window.console && console.log) {
            console.log(
                '%c个人博客 %cv1.0',
                'color: #007bff; font-weight: bold; font-size: 14px;',
                'color: #6c757d; font-size: 12px;'
            );
        }
    });

})();
