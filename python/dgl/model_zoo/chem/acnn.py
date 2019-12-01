import itertools
import numpy as np
import torch
import torch.nn as nn

from ... import to_hetero
from ... import backend
from ...nn.pytorch import AtomicConv

class ACNNPredictor(nn.Module):
    """"""
    def __init__(self, in_size, hidden_sizes, dropouts, features_to_use, num_tasks):
        super(ACNNPredictor, self).__init__()

        if type(features_to_use) != type(None):
            in_size *= len(features_to_use)

        self.project = self._build_projector(in_size, hidden_sizes, dropouts, num_tasks)

    def _build_projector(self, in_size, hidden_sizes, dropouts, num_tasks):
        modules = []
        for i, h in enumerate(hidden_sizes):
            modules.append(nn.Linear(in_size, h))
            modules.append(nn.ReLU())
            modules.append(nn.Dropout(dropouts[i]))
            in_size = h
        modules.append(nn.Linear(in_size, num_tasks))

        return nn.Sequential(*modules)

    @staticmethod
    def sum_nodes(batch_size, batch_num_nodes, feats):
        """"""
        seg_id = torch.from_numpy(np.arange(batch_size, dtype='int64').repeat(batch_num_nodes))
        seg_id = seg_id.to(feats.device)

        return backend.unsorted_1d_segment_sum(feats, seg_id, batch_size, 0)

    def forward(self, protein_graph, ligand_graph, complex_graph,
                protein_conv_out, ligand_conv_out, complex_conv_out):
        """
        Parameters
        ----------
        graph
        protein_conv_out : float32 tensor of shape (V1, K * F)
        ligand_conv_out : float32 tensor of shape (V2, K * F)
        complex_conv_out : float32 tensor of shape ((V1 + V2), K * F)
        """
        protein_feats = self.project(protein_conv_out)
        ligand_feats = self.project(ligand_conv_out)
        complex_feats = self.project(complex_conv_out)

        protein_energy = self.sum_nodes(protein_graph.batch_size,
                                        protein_graph.batch_num_nodes,
                                        protein_feats)
        ligand_energy = self.sum_nodes(ligand_graph.batch_size,
                                       ligand_graph.batch_num_nodes,
                                       ligand_feats)

        with complex_graph.local_scope():
            complex_graph.ndata['h'] = complex_feats
            hetero_complex_graph = to_hetero(
                complex_graph, ntypes=complex_graph.original_ntypes,
                etypes=complex_graph.original_etypes)
            complex_energy_protein = self.sum_nodes(
                complex_graph.batch_size, complex_graph.batch_num_protein_nodes,
                hetero_complex_graph.nodes['protein_atom'].data['h'])
            complex_energy_ligand = self.sum_nodes(
                complex_graph.batch_size, complex_graph.batch_num_ligand_nodes,
                hetero_complex_graph.nodes['ligand_atom'].data['h'])
            complex_energy = complex_energy_protein + complex_energy_ligand

        return complex_energy - (protein_energy + ligand_energy)

class ACNN(nn.Module):
    """"""
    def __init__(self, hidden_sizes, dropouts, features_to_use=None, radial=None, num_tasks=1):
        super(ACNN, self).__init__()

        if radial is None:
            radial = [[12.0], [0.0, 2.0, 4.0, 6.0, 8.0], [4.0]]
        radial_params = [x for x in itertools.product(*radial)]
        radial_params = torch.stack(list(map(torch.tensor, zip(*radial_params))), dim=1)

        self.protein_conv = AtomicConv(radial_params, features_to_use)
        self.ligand_conv = AtomicConv(radial_params, features_to_use)
        self.complex_conv = AtomicConv(radial_params, features_to_use)
        self.predictor = ACNNPredictor(radial_params.shape[0], hidden_sizes, dropouts,
                                       features_to_use, num_tasks)

    def forward(self, graph):
        protein_graph = graph[('protein_atom', 'protein', 'protein_atom')]
        # Todo (Mufei): remove the two lines below after better built-in support
        protein_graph.batch_size = graph.batch_size
        protein_graph.batch_num_nodes = graph.batch_num_nodes('protein_atom')

        protein_graph_node_feats = protein_graph.ndata['atomic_number']
        assert protein_graph_node_feats.shape[-1] == 1
        protein_graph_distances = protein_graph.edata['distance']
        protein_conv_out = self.protein_conv(protein_graph,
                                             protein_graph_node_feats,
                                             protein_graph_distances)

        ligand_graph = graph[('ligand_atom', 'ligand', 'ligand_atom')]
        # Todo (Mufei): remove the two lines below after better built-in support
        ligand_graph.batch_size = graph.batch_size
        ligand_graph.batch_num_nodes = graph.batch_num_nodes('ligand_atom')

        ligand_graph_node_feats = ligand_graph.ndata['atomic_number']
        assert ligand_graph_node_feats.shape[-1] == 1
        ligand_graph_distances = ligand_graph.edata['distance']
        ligand_conv_out = self.ligand_conv(ligand_graph,
                                           ligand_graph_node_feats,
                                           ligand_graph_distances)

        complex_graph = graph[:, 'complex', :]
        # Todo (Mufei): remove the four lines below after better built-in support
        complex_graph.batch_size = graph.batch_size
        complex_graph.original_ntypes = graph.ntypes
        complex_graph.original_etypes = graph.etypes
        complex_graph.batch_num_protein_nodes = graph.batch_num_nodes('protein_atom')
        complex_graph.batch_num_ligand_nodes = graph.batch_num_nodes('ligand_atom')

        complex_graph_node_feats = complex_graph.ndata['atomic_number']
        assert complex_graph_node_feats.shape[-1] == 1
        complex_graph_distances = complex_graph.edata['distance']
        complex_conv_out = self.complex_conv(complex_graph,
                                             complex_graph_node_feats,
                                             complex_graph_distances)

        return self.predictor(
            protein_graph, ligand_graph, complex_graph,
            protein_conv_out, ligand_conv_out, complex_conv_out)