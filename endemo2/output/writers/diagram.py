from endemo2.output.grapthical_output import GraphDataPreparer, Visualizer


class DiagramOutputMixin:

    def _write_diagrams(self):
        """Generate and save Sankey diagrams"""
        # Prepare data
        plot_data_preparer = GraphDataPreparer(self.data)
        plot_data = plot_data_preparer.prepare_data()
        # Create visualizations
        visualizer = Visualizer(plot_data)
        visualizer.create_interactive_dashboard()
