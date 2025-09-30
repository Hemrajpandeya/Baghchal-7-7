
import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

EMPTY, GOAT, TIGER, ROCK = 0, 1, 2, 3

def idx(r: int, c: int, N: int) -> int:
    return r*N + c

def rcOf(i: int, N: int):
    return divmod(i, N)

def build_adj(N: int) -> List[List[int]]:
    ADJ: List[List[int]] = [[] for _ in range(N*N)]
    dirs4 = [(1,0),(-1,0),(0,1),(0,-1)]
    dirs8 = dirs4 + [(1,1),(1,-1),(-1,1),(-1,-1)]
    for r in range(N):
        for c in range(N):
            here = idx(r,c,N)
            use = dirs8 if ((r+c)%2==0) else dirs4
            for dr,dc in use:
                rr,cc = r+dr, c+dc
                if 0<=rr<N and 0<=cc<N:
                    ADJ[here].append(idx(rr,cc,N))
    return ADJ

def build_jumps(N: int, ADJ: List[List[int]]) -> List[List[Tuple[int,int]]]:
    JUMPS: List[List[Tuple[int,int]]] = [[] for _ in range(N*N)]
    for r in range(N):
        for c in range(N):
            src = idx(r,c,N)
            for over in ADJ[src]:
                r0,c0 = rcOf(src,N); r1,c1 = rcOf(over,N)
                dr, dc = r1 - r0, c1 - c0
                r2, c2 = r1 + dr, c1 + dc
                if 0<=r2<N and 0<=c2<N:
                    land = idx(r2,c2,N)
                    if land in ADJ[over]:
                        JUMPS[src].append((over, land))
    return JUMPS

def edge_midpoint_sanctuaries(N: int) -> List[int]:
    k = N//2
    return [idx(0,k,N), idx(N-1,k,N), idx(k,0,N), idx(k,N-1,N)]

@dataclass
class Rules:
    N: int
    goats_to_place: int
    capture_to_win: int
    ADJ: List[List[int]]
    JUMPS: List[List[Tuple[int,int]]]
    safe_nodes: set = field(default_factory=set)
    enable_multijump: bool = True
    enable_ko: bool = True

def make_7x7_rules() -> Rules:
    N = 7
    ADJ = build_adj(N)
    JUMPS = build_jumps(N, ADJ)
    return Rules(
        N=N,
        goats_to_place=30,
        capture_to_win=8,
        ADJ=ADJ,
        JUMPS=JUMPS,
        safe_nodes=set(edge_midpoint_sanctuaries(N)),
        enable_multijump=True,
        enable_ko=True,
    )

@dataclass
class GameState:
    board: List[int]
    goats_placed: int
    goats_captured: int
    player: str
    move_count: int
    chain_active: bool = False
    chain_src: Optional[int] = None
    seen_counts: Dict[Tuple[int,...], int] = field(default_factory=dict)

def initial_state(rules: Rules) -> GameState:
    N = rules.N
    b = [EMPTY]*(N*N)
    for i in (0, N-1, N*(N-1), N*N-1):
        b[i] = TIGER
    gs = GameState(board=b, goats_placed=0, goats_captured=0, player='goat', move_count=0)
    key = tuple(gs.board)
    gs.seen_counts[key] = gs.seen_counts.get(key, 0) + 1
    return gs

def phase(gs: GameState, rules: Rules) -> str:
    return 'placement' if gs.goats_placed < rules.goats_to_place else 'movement'

def tiger_has_more_jumps_from(pos: int, gs: GameState, rules: Rules) -> bool:
    b = gs.board
    for over, land in rules.JUMPS[pos]:
        if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
            return True
    return False

def legal_actions(gs: GameState, rules: Rules, role: Optional[str]=None):
    role = role or gs.player
    acts = []
    b = gs.board
    N = rules.N
    if role == 'goat':
        if gs.chain_active:
            return []
        if phase(gs, rules) == 'placement':
            for i in range(N*N):
                if b[i]==EMPTY:
                    acts.append(('place', i))
        else:
            for i in range(N*N):
                if b[i]==GOAT:
                    for d in rules.ADJ[i]:
                        if b[d]==EMPTY:
                            acts.append(('move', i, d))
    else: # tiger
        if gs.chain_active and gs.chain_src is not None and rules.enable_multijump:
            i = gs.chain_src
            for over, land in rules.JUMPS[i]:
                if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                    acts.append(('jump', i, land))
            return acts
        for i in range(N*N):
            if b[i]==TIGER:
                for d in rules.ADJ[i]:
                    if b[d]==EMPTY:
                        acts.append(('move', i, d))
                for over, land in rules.JUMPS[i]:
                    if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                        acts.append(('jump', i, land))
    return acts

def is_terminal(gs: GameState, rules: Rules):
    if rules.enable_ko:
        key = tuple(gs.board)
        if gs.seen_counts.get(key, 0) >= 3:
            return True, 'draw'
    if gs.goats_captured >= rules.capture_to_win:
        return True, 'tiger'
    if gs.player == 'tiger' and not legal_actions(gs, rules, 'tiger'):
        return True, 'goat'
    if gs.move_count >= 1200:
        return True, 'draw'
    return False, None

def apply(gs: GameState, rules: Rules, action):
    kind = action[0]
    b = gs.board
    if gs.player == 'goat':
        if gs.chain_active:
            return False
        if kind == 'place' and phase(gs, rules) == 'placement':
            _, dst = action
            if b[dst] != EMPTY:
                return False
            b[dst] = GOAT
            gs.goats_placed += 1
            gs.player = 'tiger'
            gs.move_count += 1
        elif kind == 'move' and phase(gs, rules) == 'movement':
            _, src, dst = action
            if b[src]==GOAT and b[dst]==EMPTY and dst in rules.ADJ[src]:
                b[src], b[dst] = EMPTY, GOAT
                gs.player = 'tiger'
                gs.move_count += 1
            else:
                return False
        else:
            return False
    else:
        if kind == 'move':
            if gs.chain_active:
                return False
            _, src, dst = action
            if b[src]==TIGER and b[dst]==EMPTY and dst in rules.ADJ[src]:
                b[src], b[dst] = EMPTY, TIGER
                gs.player = 'goat'
                gs.move_count += 1
            else:
                return False
        elif kind == 'jump':
            _, src, dst = action
            if gs.chain_active and src != gs.chain_src:
                return False
            over = None
            for o,l in rules.JUMPS[src]:
                if l==dst:
                    over=o; break
            if over is None or b[src]!=TIGER or b[over]!=GOAT or b[dst]!=EMPTY or (over in rules.safe_nodes):
                return False
            b[src], b[over], b[dst] = EMPTY, EMPTY, TIGER
            gs.goats_captured += 1
            gs.move_count += 1
            if rules.enable_multijump and tiger_has_more_jumps_from(dst, gs, rules):
                gs.player = 'tiger'
                gs.chain_active = True
                gs.chain_src = dst
            else:
                gs.player = 'goat'
                gs.chain_active = False
                gs.chain_src = None
        else:
            return False
    if rules.enable_ko:
        key = tuple(gs.board)
        gs.seen_counts[key] = gs.seen_counts.get(key, 0) + 1
    return True

def tiger_greedy(gs: GameState, rules: Rules):
    b = gs.board; N = rules.N
    if gs.chain_active and gs.chain_src is not None:
        i = gs.chain_src
        best = None; best_next = -1
        for over, land in rules.JUMPS[i]:
            if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                nxt = 0
                for o2, l2 in rules.JUMPS[land]:
                    if b[o2]==GOAT and (o2 not in rules.safe_nodes) and b[l2]==EMPTY:
                        nxt += 1
                if nxt > best_next:
                    best_next, best = nxt, ('jump', i, land)
        return best
    for i in range(N*N):
        if b[i]==TIGER:
            for over, land in rules.JUMPS[i]:
                if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                    return ('jump', i, land)
    best = None; best_mob = -1
    for i in range(N*N):
        if b[i]==TIGER:
            for d in rules.ADJ[i]:
                if b[d]==EMPTY:
                    b[i], b[d] = EMPTY, TIGER
                    mob = 0
                    for t in range(N*N):
                        if b[t]==TIGER:
                            mob += sum(1 for x in rules.ADJ[t] if b[x]==EMPTY)
                            for over, land in rules.JUMPS[t]:
                                if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                                    mob += 1
                    if mob > best_mob:
                        best_mob, best = mob, ('move', i, d)
                    b[i], b[d] = TIGER, EMPTY
    return best

def goat_greedy(gs: GameState, rules: Rules):
    b = gs.board; N = rules.N
    if phase(gs, rules)=='placement':
        best = None; best_mob = 10**9
        for dst in range(N*N):
            if b[dst]==EMPTY:
                danger = any(b[n]==TIGER for n in rules.ADJ[dst])
                b[dst] = GOAT
                mob = 0
                for t in range(N*N):
                    if b[t]==TIGER:
                        mob += sum(1 for x in rules.ADJ[t] if b[x]==EMPTY)
                        for over, land in rules.JUMPS[t]:
                            if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                                mob += 1
                if danger:
                    mob += 3
                if mob < best_mob:
                    best_mob, best = mob, ('place', dst)
                b[dst] = EMPTY
        return best
    best = None; best_mob = 10**9
    for g in range(N*N):
        if b[g]==GOAT:
            for d in rules.ADJ[g]:
                if b[d]==EMPTY:
                    b[g], b[d] = EMPTY, GOAT
                    mob = 0
                    for t in range(N*N):
                        if b[t]==TIGER:
                            mob += sum(1 for x in rules.ADJ[t] if b[x]==EMPTY)
                            for over, land in rules.JUMPS[t]:
                                if b[over]==GOAT and (over not in rules.safe_nodes) and b[land]==EMPTY:
                                    mob += 1
                    if mob < best_mob:
                        best_mob, best = mob, ('move', g, d)
                    b[g], b[d] = GOAT, EMPTY
    return best

class BaghChal7x7GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bagh-Chal 7×7 — Multi-Jump + Sanctuaries + KO")
        self.rules = make_7x7_rules()
        self.state = initial_state(self.rules)
        self.human_role = 'goat'
        self.ai_role = 'tiger'
        self.selected: Optional[int] = None
        self.legal_dest: List[int] = []

        self.frame = tk.Frame(root)
        self.frame.pack(padx=8, pady=8)
        self.info = tk.Label(self.frame, text="", font=("Arial", 12), justify="left")
        self.info.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,6))

        top = tk.Frame(self.frame)
        top.grid(row=1, column=0, columnspan=3, sticky="we")
        tk.Button(top, text="New 7×7 Game", command=self.on_new).pack(side="left", padx=4)
        tk.Label(top, text="You play:").pack(side="left", padx=(12,4))
        self.side_var = tk.StringVar(value=self.human_role)
        tk.OptionMenu(top, self.side_var, "goat", "tiger", command=self.on_side_change).pack(side="left")
        tk.Label(top, text="Goats to place").pack(side="left", padx=(12,4))
        self.goats_var = tk.IntVar(value=self.rules.goats_to_place)
        tk.Spinbox(top, from_=24, to=40, width=4, textvariable=self.goats_var, command=self.on_param_change).pack(side="left")
        tk.Label(top, text="Captures to win").pack(side="left", padx=(12,4))
        self.captures_var = tk.IntVar(value=self.rules.capture_to_win)
        tk.Spinbox(top, from_=6, to=12, width=4, textvariable=self.captures_var, command=self.on_param_change).pack(side="left")
        self.mj_var = tk.BooleanVar(value=self.rules.enable_multijump)
        tk.Checkbutton(top, text="Multi-jump", variable=self.mj_var, command=self.on_param_change).pack(side="left", padx=(12,4))
        self.ko_var = tk.BooleanVar(value=self.rules.enable_ko)
        tk.Checkbutton(top, text="KO (threefold draw)", variable=self.ko_var, command=self.on_param_change).pack(side="left", padx=(6,4))

        self.size_px = 620
        self.padding = 32
        self.canvas = tk.Canvas(self.frame, width=self.size_px, height=self.size_px, bg="white", highlightthickness=0)
        self.canvas.grid(row=2, column=0, columnspan=3)
        self.canvas.bind("<Button-1>", self.on_click)

        self.compute_points()
        self.draw_board()
        self.update_info()
        self.root.after(50, self.maybe_ai_opening)

    def on_param_change(self):
        self.rules.goats_to_place = int(self.goats_var.get())
        self.rules.capture_to_win = int(self.captures_var.get())
        self.rules.enable_multijump = bool(self.mj_var.get())
        self.rules.enable_ko = bool(self.ko_var.get())
        self.on_new()

    def compute_points(self):
        N = self.rules.N
        step = (self.size_px - 2*self.padding) / (N-1)
        self.step = step
        self.points = [(self.padding + c*step, self.padding + r*step) for r in range(N) for c in range(N)]

    def on_new(self):
        self.state = initial_state(self.rules)
        self.selected = None
        self.legal_dest = []
        self.compute_points()
        self.update_info()
        self.draw_board()
        self.root.after(50, self.maybe_ai_opening)

    def on_side_change(self, _=None):
        self.human_role = self.side_var.get()
        self.ai_role = 'tiger' if self.human_role=='goat' else 'goat'
        self.on_new()

    def update_info(self, status: Optional[str]=None):
        ph = phase(self.state, self.rules)
        txt = (
            f"Board: 7×7   |   Player to move: {self.state.player.upper()}   |   Phase: {ph}\n"
            f"Goats placed: {self.state.goats_placed}/{self.rules.goats_to_place}   |   "
            f"Goats captured: {self.state.goats_captured} (Tigers win at {self.rules.capture_to_win})   |   "
            f"Ply: {self.state.move_count}"
        )
        if self.rules.safe_nodes:
            txt += "\nSanctuaries at edge midpoints (goats here cannot be captured)."
        if status:
            txt += f"\n{status}"
        self.info.config(text=txt)

    def draw_board(self):
        self.canvas.delete("all")
        ADJ = self.rules.ADJ
        for i, nbrs in enumerate(ADJ):
            x1,y1 = self.points[i]
            for j in nbrs:
                if j>i:
                    x2,y2 = self.points[j]
                    self.canvas.create_line(x1,y1,x2,y2, fill="#888", width=2)
        for i in self.rules.safe_nodes:
            x,y = self.points[i]
            r = max(12, int(self.step*0.25))
            self.canvas.create_oval(x-r,y-r,x+r,y+r, outline="#8b5cf6", width=3, dash=(4,3))
        r_sel = self.selected
        radius = max(9, int(self.step*0.22))
        hlrad  = max(13, int(self.step*0.27))
        for i,(x,y) in enumerate(self.points):
            if i in self.legal_dest:
                self.canvas.create_oval(x-hlrad,y-hlrad,x+hlrad,y+hlrad, fill="#dbeafe", outline="#2563eb", width=3)
            v = self.state.board[i]
            if v==TIGER:
                fill, outline = "#fb923c", "#1f2937"
            elif v==GOAT:
                fill, outline = "#10b981", "#1f2937"
            elif v==ROCK:
                fill, outline = "#9ca3af", "#374151"
            else:
                fill, outline = "#e5e7eb", "#4b5563"
            self.canvas.create_oval(x-radius,y-radius,x+radius,y+radius, fill=fill, outline=outline, width=2)
            if r_sel==i:
                self.canvas.create_oval(x-hlrad,y-hlrad,x+hlrad,y+hlrad, outline="#0ea5e9", width=3)
            self.canvas.create_text(x, y+1, text=str(i), fill="#374151", font=("Arial", max(8, int(self.step*0.18))))

    def on_click(self, event):
        if self.state.player != self.human_role:
            return
        node = self.pick_node(event.x, event.y)
        if node is None:
            return
        if self.human_role=='goat' and phase(self.state, self.rules)=='placement':
            if apply(self.state, self.rules, ('place', node)):
                self.after_human_move()
            else:
                self.update_info("Illegal placement.")
                self.draw_board()
            return
        if self.selected is None:
            if (self.human_role=='goat' and self.state.board[node]==GOAT) or (self.human_role=='tiger' and self.state.board[node]==TIGER):
                if self.state.chain_active and self.human_role=='tiger' and node != self.state.chain_src:
                    return
                self.selected = node
                self.legal_dest = self.collect_dests(node)
                self.draw_board()
        else:
            src = self.selected
            if self.human_role=='goat':
                if node in self.rules.ADJ[src] and self.state.board[node]==EMPTY:
                    if apply(self.state, self.rules, ('move', src, node)):
                        self.selected=None
                        self.legal_dest=[]
                        self.after_human_move()
                        return
            else:
                is_jump = any((land==node and self.state.board[over]==GOAT and (over not in self.rules.safe_nodes) and self.state.board[land]==EMPTY)
                              for over,land in self.rules.JUMPS[src])
                if is_jump:
                    if apply(self.state, self.rules, ('jump', src, node)):
                        if self.state.chain_active and self.state.player=='tiger':
                            self.selected = self.state.chain_src
                            self.legal_dest = self.collect_dests(self.selected)
                            self.update_info("Tiger may continue jumping…")
                            self.draw_board()
                            return
                        else:
                            self.selected=None
                            self.legal_dest=[]
                            self.after_human_move()
                            return
                elif (not self.state.chain_active) and node in self.rules.ADJ[src] and self.state.board[node]==EMPTY:
                    if apply(self.state, self.rules, ('move', src, node)):
                        self.selected=None
                        self.legal_dest=[]
                        self.after_human_move()
                        return
            if node != src:
                self.selected=None
                self.legal_dest=[]
                self.draw_board()

    def collect_dests(self, src:int):
        dests = []
        if self.human_role=='goat':
            for d in self.rules.ADJ[src]:
                if self.state.board[d]==EMPTY:
                    dests.append(d)
        else:
            if self.state.chain_active and self.state.chain_src is not None and src != self.state.chain_src:
                return []
            any_jump = False
            for over, land in self.rules.JUMPS[src]:
                if self.state.board[over]==GOAT and (over not in self.rules.safe_nodes) and self.state.board[land]==EMPTY:
                    dests.append(land)
                    any_jump = True
            if not any_jump and (not self.state.chain_active):
                for d in self.rules.ADJ[src]:
                    if self.state.board[d]==EMPTY:
                        dests.append(d)
        return dests

    def pick_node(self, x, y) -> Optional[int]:
        rad2 = (max(9, int(self.step*0.22)) + 6)**2
        for i,(px,py) in enumerate(self.points):
            if (x-px)**2 + (y-py)**2 <= rad2:
                return i
        return None

    def after_human_move(self):
        term, winner = is_terminal(self.state, self.rules)
        self.update_info()
        self.draw_board()
        if term:
            self.end_game(winner)
            return
        self.root.after(280, self.ai_move)

    def ai_move(self):
        if self.state.player != self.ai_role:
            return
        while self.state.player == self.ai_role:
            if self.ai_role=='tiger':
                act = tiger_greedy(self.state, self.rules)
            else:
                act = goat_greedy(self.state, self.rules)
            if act is None:
                break
            apply(self.state, self.rules, act)
            if self.ai_role == 'goat':
                break
            if act[0] != 'jump' and self.state.chain_active:
                break
            if act[0] == 'move':
                break
        self.update_info()
        self.draw_board()
        term, winner = is_terminal(self.state, self.rules)
        if term:
            self.end_game(winner)

    def maybe_ai_opening(self):
        if self.ai_role=='goat' and self.state.player=='goat' and phase(self.state, self.rules)=='placement':
            act = goat_greedy(self.state, self.rules)
            if act:
                apply(self.state, self.rules, act)
            self.update_info()
            self.draw_board()

    def end_game(self, winner):
        message = "Draw (KO or move cap)." if winner=='draw' else f"{winner.upper()} wins!"
        self.update_info(message)
        messagebox.showinfo("Game Over", message)

if __name__ == '__main__':
    root = tk.Tk()
    app = BaghChal7x7GUI(root)
    root.mainloop()
