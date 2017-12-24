from utils import *
import cplex

def parser(filename):
    G = nx.Graph()   
    asd = os.getcwd()    
    with open(filename) as f:
        for line in f:
            if line.startswith("e"):
                splitted_line = line.split(" ")
                G.add_edge(int(splitted_line[1]), int(splitted_line[2]))   
    return(G)

class branch_and_bound:
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.nodes = self.graph.nodes()
        self.ind_sets = []
        self.get_ind_sets()
        self.not_connected = nx.complement(self.graph).edges()
        self.init_problem = self.construct_problem()
        self.current_maximum_clique_len = 0

    def get_ind_sets(self):
        strategies = [nx.coloring.strategy_independent_set]

        for strategy in strategies:
            d = nx.coloring.greedy_color(self.graph, strategy=strategy)
            print(type(d))
            for color in set(color for node, color in d.items()):
                self.ind_sets.append(
                    [key for key, value in d.items() if value == color])

    def get_branching_variable(self, solution: list):
        return next((index for index, value in enumerate(solution) if not value.is_integer()), None)

    def construct_problem(self):
        '''
        Construct LP-relaxation of max clique problem
        nodes: list of names of all nodes in graph
        ind_sets: list of independent sets (each as list of nodes names)
        Problem\n
        x1 + x2 + ... + xn -> max\n
        xk + ... + xl <= 1  (ind_set_num times, [k...l] - nodes from independent set)\n
        0 <= x1 <= 1\n
        ...\n
        0 <= xn <= 1\n
        xi + xj <= 1, for every pair (i,j) which doesn't connected by edge\n
        '''
        obj = [1.0] * len(self.nodes)
        upper_bounds = [1.0] * len(self.nodes)
        types = 'C' * len(self.nodes)
        # lower bounds are all 0.0 (the default)
        columns_names = ['x{0}'.format(x) for x in self.nodes]
        right_hand_side = [1.0] * \
            (len(self.ind_sets) + len(self.not_connected))
        name_iter = iter(range(len(self.ind_sets) + len(self.nodes)**2))
        constraint_names = ['c{0}'.format(next(name_iter)) for x in range(
            (len(self.ind_sets) + len(self.not_connected)))]
        constraint_senses = ['L'] * \
            (len(self.ind_sets) + len(self.not_connected))

        problem = cplex.Cplex()

        problem.objective.set_sense(problem.objective.sense.maximize)
        problem.variables.add(obj=obj, ub=upper_bounds,
                              names=columns_names, types=types)

        constraints = []
        for ind_set in self.ind_sets:
            constraints.append([['x{0}'.format(x)
                                 for x in ind_set], [1.0] * len(ind_set)])
        for xi, xj in self.not_connected:
            constraints.append(
                [['x{0}'.format(xi), 'x{0}'.format(xj)], [1.0, 1.0]])

        problem.linear_constraints.add(lin_expr=constraints,
                                       senses=constraint_senses,
                                       rhs=right_hand_side,
                                       names=constraint_names)
        return problem

    def branching(self, problem: cplex.Cplex):
        def add_constraint(problem: cplex.Cplex, bv: float, rhs: float):
            problem.linear_constraints.add(lin_expr=[[[bv], [1.0]]],
                                           senses=['E'],
                                           rhs=[rhs],
                                           names=['branch_{0}_{1}'.format(bv, rhs)])
            return problem
        try:
            problem.solve()
            solution = problem.solution.get_values()
        except cplex.exceptions.CplexSolverError:
            return 0
        print(solution)
        if sum(solution) > self.current_maximum_clique_len:
            bvar = self.get_branching_variable(solution)
            if bvar is None:
                self.current_maximum_clique_len = len(
                    list(filter(lambda x: x == 1.0, solution)))
                print('MAX_LEN', self.current_maximum_clique_len)
                return self.current_maximum_clique_len, solution
            return max(self.branching(add_constraint(cplex.Cplex(problem), bvar, 1.0)),
                       self.branching(add_constraint(cplex.Cplex(problem), bvar, 0.0)),
                       key=lambda x: x[0] if isinstance(x, (list, tuple)) else x)
        return 0

    @timing
    def solve(self):
        return self.branching(self.init_problem)


def main():
    #args = arguments()
    graph = parser('MANN_a9.clq.txt')
    try:
        solution, extime = branch_and_bound(graph).solve()

        print('Maximum clique size:', solution[0])
        print('Nodes:', list(index + 1 for index,
                                value in enumerate(solution[1]) if value == 1.0))
    except TimeoutException:
        print("Timed out!")
        sys.exit(0)


if __name__ == '__main__':
    main()