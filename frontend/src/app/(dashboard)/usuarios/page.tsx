"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { ChevronDownIcon, SearchIcon } from "@/components/icons";
import styles from "./usuarios.module.css";

interface User {
  id: string;
  auth_uid: string;
  nome: string;
  email: string;
  setor: string;
  localizacao: string | null;
  is_admin: boolean;
  ativo: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

interface ListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

type ModalMode = null | "create" | "edit" | "deactivate";

const SETORES = ["STUDIO", "VENDEDOR", "MOTORISTA", "CLICHERIA"] as const;
const LOCALIZACOES = ["MATRIZ", "FILIAL"] as const;

/** Get a fresh access token from the current Supabase session. */
async function getToken(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export default function UsuariosPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [busca, setBusca] = useState("");
  const [filtroSetor, setFiltroSetor] = useState("");
  const [filtroAtivo, setFiltroAtivo] = useState("");

  // Modal state
  const [modal, setModal] = useState<ModalMode>(null);
  const [modalUser, setModalUser] = useState<User | null>(null);
  const [modalError, setModalError] = useState("");
  const [modalLoading, setModalLoading] = useState(false);

  // Form fields
  const [fNome, setFNome] = useState("");
  const [fEmail, setFEmail] = useState("");
  const [fSenha, setFSenha] = useState("");
  const [fSetor, setFSetor] = useState<string>("STUDIO");
  const [fLocalizacao, setFLocalizacao] = useState<string>("");
  const [fIsAdmin, setFIsAdmin] = useState(false);

  const fetchUsers = useCallback(async () => {
    const token = await getToken();
    if (!token) return;
    setLoading(true);
    setListError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "20",
      });
      if (busca) params.set("busca", busca);
      if (filtroSetor) params.set("setor", filtroSetor);
      if (filtroAtivo) params.set("ativo", filtroAtivo);

      const res = await apiFetch<ListResponse>(
        `/api/v1/users/?${params.toString()}`,
        { token }
      );
      setData(res);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Falha ao carregar usuarios. Verifique sua conexao.";
      setListError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [page, busca, filtroSetor, filtroAtivo]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // ── Modal helpers ─────────────────────────────────────────────────────────

  function openCreate() {
    setModal("create");
    setModalUser(null);
    setModalError("");
    setFNome("");
    setFEmail("");
    setFSenha("");
    setFSetor("STUDIO");
    setFLocalizacao("");
    setFIsAdmin(false);
  }

  function openEdit(u: User) {
    setModal("edit");
    setModalUser(u);
    setModalError("");
    setFNome(u.nome);
    setFSetor(u.setor);
    setFLocalizacao(u.localizacao || "");
    setFIsAdmin(u.is_admin);
  }

  function openDeactivate(u: User) {
    setModal("deactivate");
    setModalUser(u);
    setModalError("");
  }

  function closeModal() {
    setModal(null);
    setModalUser(null);
    setModalError("");
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    const token = await getToken();
    if (!token) return;
    setModalLoading(true);
    setModalError("");
    try {
      await apiFetch("/api/v1/users/", {
        method: "POST",
        token,
        body: JSON.stringify({
          nome: fNome,
          email: fEmail,
          senha: fSenha,
          setor: fSetor,
          localizacao: fSetor === "VENDEDOR" ? fLocalizacao || null : null,
          is_admin: fIsAdmin,
        }),
      });
      closeModal();
      fetchUsers();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Erro ao criar");
    } finally {
      setModalLoading(false);
    }
  }

  async function handleEdit(e: FormEvent) {
    e.preventDefault();
    if (!modalUser) return;
    const token = await getToken();
    if (!token) return;
    setModalLoading(true);
    setModalError("");
    try {
      const body: Record<string, unknown> = {};
      if (fNome !== modalUser.nome) body.nome = fNome;
      if (fSetor !== modalUser.setor) body.setor = fSetor;
      if (fSetor === "VENDEDOR") {
        if (fLocalizacao !== (modalUser.localizacao || ""))
          body.localizacao = fLocalizacao || null;
      } else {
        body.localizacao = null;
      }
      if (fIsAdmin !== modalUser.is_admin) body.is_admin = fIsAdmin;

      if (Object.keys(body).length === 0) {
        closeModal();
        return;
      }

      await apiFetch(`/api/v1/users/${modalUser.id}`, {
        method: "PATCH",
        token,
        body: JSON.stringify(body),
      });
      closeModal();
      fetchUsers();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Erro ao editar");
    } finally {
      setModalLoading(false);
    }
  }

  async function handleDeactivate() {
    if (!modalUser) return;
    const token = await getToken();
    if (!token) return;
    setModalLoading(true);
    setModalError("");
    try {
      await apiFetch(`/api/v1/users/${modalUser.id}`, {
        method: "DELETE",
        token,
      });
      closeModal();
      fetchUsers();
    } catch (err) {
      setModalError(
        err instanceof ApiError ? err.message : "Erro ao desativar"
      );
    } finally {
      setModalLoading(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Aviso mostrado apenas em viewports mobile — o recurso nao esta disponivel
          no tamanho reduzido e a versao desktop continua totalmente funcional. */}
      <div className={styles.mobileNotice}>
        <p>Para acessar esse recurso, acesse a versão desktop.</p>
      </div>

      <div className={styles.desktopOnly}>
      <header className={styles.pageHeader}>
        <h1 className={styles.title}>Gerenciador de usuarios</h1>
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={openCreate}
        >
          Novo usuario
        </button>
      </header>

      <section className={styles.filters}>
        <div className={styles.searchField}>
          <SearchIcon className={styles.searchIcon} aria-hidden="true" />
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Buscar por nome ou email..."
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className={styles.selectField}>
          <select
            className={styles.select}
            value={filtroSetor}
            onChange={(e) => {
              setFiltroSetor(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos os setores</option>
            {SETORES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <ChevronDownIcon className={styles.selectChevron} aria-hidden="true" />
        </div>

        <div className={styles.selectField}>
          <select
            className={styles.select}
            value={filtroAtivo}
            onChange={(e) => {
              setFiltroAtivo(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos</option>
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
          </select>
          <ChevronDownIcon className={styles.selectChevron} aria-hidden="true" />
        </div>
      </section>

      <section className={styles.tableWrap}>
        <div className={styles.tableScroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Setor</th>
              <th>Localização</th>
              <th>Status</th>
              <th>Perfil</th>
              <th className={styles.thActions}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? (
              <tr>
                <td colSpan={7} className={styles.stateCell}>
                  Carregando...
                </td>
              </tr>
            ) : listError ? (
              <tr>
                <td colSpan={7} className={styles.errorCell}>
                  <div className={styles.errorMessage}>{listError}</div>
                  <button
                    type="button"
                    className={styles.retryBtn}
                    onClick={fetchUsers}
                  >
                    Tentar novamente
                  </button>
                </td>
              </tr>
            ) : data && data.items.length > 0 ? (
              data.items.map((u) => (
                <tr key={u.id}>
                  <td>{u.nome}</td>
                  <td>{u.email}</td>
                  <td>{u.setor}</td>
                  <td>{u.localizacao || "—"}</td>
                  <td>
                    <span
                      className={
                        u.ativo ? styles.statusActive : styles.statusInactive
                      }
                    >
                      {u.ativo ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td>{u.is_admin ? "Admin" : "—"}</td>
                  <td>
                    <div className={styles.actions}>
                      <button
                        type="button"
                        className={styles.editBtn}
                        onClick={() => openEdit(u)}
                      >
                        Editar
                      </button>
                      {u.ativo && (
                        <button
                          type="button"
                          className={styles.dangerBtn}
                          onClick={() => openDeactivate(u)}
                        >
                          Desativar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className={styles.stateCell}>
                  Nenhum usuario encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </section>

      {data && data.pages > 1 && (
        <div className={styles.pagination}>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Anterior
          </button>
          <span className={styles.pageInfo}>
            Pagina {data.page} de {data.pages} ({data.total} registros)
          </span>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Proxima
          </button>
        </div>
      )}
      </div>

      {/* ── Create Modal ──────────────────────────────────────────────────── */}
      {modal === "create" && (
        <div
          className={styles.modalOverlay}
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-create-title"
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 id="modal-create-title" className={styles.modalTitle}>
              Novo usuario
            </h2>
            <div className={styles.modalDivider} />
            {modalError && (
              <div className={styles.modalError}>{modalError}</div>
            )}
            <form className={styles.modalForm} onSubmit={handleCreate}>
              <div className={styles.modalField}>
                <label htmlFor="create-nome">Nome:</label>
                <input
                  id="create-nome"
                  required
                  maxLength={150}
                  value={fNome}
                  onChange={(e) => setFNome(e.target.value)}
                  className={styles.modalInput}
                />
              </div>
              <div className={styles.modalField}>
                <label htmlFor="create-email">E-mail:</label>
                <input
                  id="create-email"
                  required
                  type="email"
                  maxLength={255}
                  value={fEmail}
                  onChange={(e) => setFEmail(e.target.value)}
                  className={styles.modalInput}
                />
              </div>
              <div className={styles.modalField}>
                <label htmlFor="create-senha">
                  Senha (min. 8, com letra e numero):
                </label>
                <input
                  id="create-senha"
                  required
                  type="password"
                  minLength={8}
                  maxLength={128}
                  value={fSenha}
                  onChange={(e) => setFSenha(e.target.value)}
                  className={styles.modalInput}
                  placeholder="********************"
                />
              </div>
              <div className={styles.modalField}>
                <label htmlFor="create-setor">Setor</label>
                <div className={styles.modalSelectWrap}>
                  <select
                    id="create-setor"
                    required
                    value={fSetor}
                    onChange={(e) => {
                      setFSetor(e.target.value);
                      if (e.target.value !== "VENDEDOR") setFLocalizacao("");
                    }}
                    className={styles.modalInput}
                  >
                    {SETORES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <ChevronDownIcon
                    className={styles.modalChevron}
                    aria-hidden="true"
                  />
                </div>
              </div>
              {fSetor === "VENDEDOR" && (
                <div className={styles.modalField}>
                  <label htmlFor="create-loc">Localizacao</label>
                  <div className={styles.modalSelectWrap}>
                    <select
                      id="create-loc"
                      required
                      value={fLocalizacao}
                      onChange={(e) => setFLocalizacao(e.target.value)}
                      className={styles.modalInput}
                    >
                      <option value="">Selecione...</option>
                      {LOCALIZACOES.map((l) => (
                        <option key={l} value={l}>
                          {l}
                        </option>
                      ))}
                    </select>
                    <ChevronDownIcon
                      className={styles.modalChevron}
                      aria-hidden="true"
                    />
                  </div>
                </div>
              )}
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  className={styles.checkInput}
                  checked={fIsAdmin}
                  onChange={(e) => setFIsAdmin(e.target.checked)}
                />
                <span className={styles.checkBox} aria-hidden="true" />
                <span>Administrador</span>
              </label>
              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={closeModal}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className={styles.btnPrimary}
                  disabled={modalLoading}
                >
                  {modalLoading ? "Cadastrando..." : "Cadastrar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Edit Modal ────────────────────────────────────────────────────── */}
      {modal === "edit" && modalUser && (
        <div
          className={styles.modalOverlay}
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-edit-title"
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 id="modal-edit-title" className={styles.modalTitle}>
              Editar usuario
            </h2>
            <div className={styles.modalDivider} />
            {modalError && (
              <div className={styles.modalError}>{modalError}</div>
            )}
            <form className={styles.modalForm} onSubmit={handleEdit}>
              <div className={styles.modalField}>
                <label htmlFor="edit-nome">Nome:</label>
                <input
                  id="edit-nome"
                  required
                  maxLength={150}
                  value={fNome}
                  onChange={(e) => setFNome(e.target.value)}
                  className={styles.modalInput}
                />
              </div>
              <div className={styles.modalField}>
                <label htmlFor="edit-email">E-mail:</label>
                <input
                  id="edit-email"
                  disabled
                  value={modalUser.email}
                  className={`${styles.modalInput} ${styles.modalInputDisabled}`}
                />
              </div>
              <div className={styles.modalField}>
                <label htmlFor="edit-setor">Setor</label>
                <div className={styles.modalSelectWrap}>
                  <select
                    id="edit-setor"
                    required
                    value={fSetor}
                    onChange={(e) => {
                      setFSetor(e.target.value);
                      if (e.target.value !== "VENDEDOR") setFLocalizacao("");
                    }}
                    className={styles.modalInput}
                  >
                    {SETORES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <ChevronDownIcon
                    className={styles.modalChevron}
                    aria-hidden="true"
                  />
                </div>
              </div>
              {fSetor === "VENDEDOR" && (
                <div className={styles.modalField}>
                  <label htmlFor="edit-loc">Localizacao</label>
                  <div className={styles.modalSelectWrap}>
                    <select
                      id="edit-loc"
                      required
                      value={fLocalizacao}
                      onChange={(e) => setFLocalizacao(e.target.value)}
                      className={styles.modalInput}
                    >
                      <option value="">Selecione...</option>
                      {LOCALIZACOES.map((l) => (
                        <option key={l} value={l}>
                          {l}
                        </option>
                      ))}
                    </select>
                    <ChevronDownIcon
                      className={styles.modalChevron}
                      aria-hidden="true"
                    />
                  </div>
                </div>
              )}
              <label className={styles.checkRow}>
                <input
                  type="checkbox"
                  className={styles.checkInput}
                  checked={fIsAdmin}
                  onChange={(e) => setFIsAdmin(e.target.checked)}
                />
                <span className={styles.checkBox} aria-hidden="true" />
                <span>Administrador</span>
              </label>
              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={styles.btnSecondary}
                  onClick={closeModal}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className={styles.btnPrimary}
                  disabled={modalLoading}
                >
                  {modalLoading ? "Salvando..." : "Salvar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Deactivate Confirmation Modal ─────────────────────────────────── */}
      {modal === "deactivate" && modalUser && (
        <div
          className={styles.modalOverlay}
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-deact-title"
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h2 id="modal-deact-title" className={styles.modalTitle}>
              Desativar usuario
            </h2>
            <div className={styles.modalDivider} />
            {modalError && (
              <div className={styles.modalError}>{modalError}</div>
            )}
            <p className={styles.modalText}>
              Tem certeza que deseja desativar{" "}
              <strong>{modalUser.nome}</strong>? O usuario nao conseguira mais
              acessar o sistema.
            </p>
            <div className={styles.modalActions}>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={closeModal}
              >
                Cancelar
              </button>
              <button
                type="button"
                className={styles.btnDanger}
                disabled={modalLoading}
                onClick={handleDeactivate}
              >
                {modalLoading ? "Desativando..." : "Desativar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
