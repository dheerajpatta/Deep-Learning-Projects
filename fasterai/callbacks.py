from fasterai.visualize import ModelStatsVisualizer, ImageGenVisualizer, WganTrainerStatsVisualizer, LearnerStatsVisualizer, ModelGraphVisualizer
from numpy import ndarray
from matplotlib.axes import Axes
from fastai.conv_learner import *
from fastai.dataset import *
from fasterai.wgan import WGANGenTrainingResult, WGANCriticTrainingResult, WGANTrainer
from fasterai.files import *
from IPython.display import display
from tensorboardX import SummaryWriter
import torchvision.utils as vutils
import shutil
import statistics


class ModelVisualizationHook():
    def __init__(self, base_dir: Path, module: nn.Module, name: str, stats_iters: int=10):
        self.base_dir = base_dir
        self.name = name
        log_dir = base_dir/name
        clear_directory(log_dir)
        self.tbwriter = SummaryWriter(log_dir=str(log_dir))
        self.hook = module.register_forward_hook(self.forward_hook)
        self.stats_iters = stats_iters
        self.iter_count = 0
        self.model_vis = ModelStatsVisualizer() 

    def forward_hook(self, module: nn.Module, input, output): 
        self.iter_count += 1
        if self.iter_count % self.stats_iters == 0:
            self.model_vis.write_tensorboard_stats(module, iter_count=self.iter_count, tbwriter=self.tbwriter)  


    def close(self):
        self.tbwriter.close()
        self.hook.remove()

class WganVisualizationHook():
    def __init__(self, base_dir: Path, trainer: WGANTrainer, name: str, stats_iters: int=10, visual_iters: int=100, jupyter:bool=False):
        super().__init__()
        self.base_dir = base_dir
        self.name = name
        log_dir = base_dir/name
        clear_directory(log_dir)
        self.tbwriter = SummaryWriter(log_dir=str(log_dir))
        self.hooks = [trainer.register_train_loop_hook(self.train_loop_hook)]
        self.hooks.append(trainer.register_train_begin_hook(self.train_begin_hook))
        self.stats_iters = stats_iters
        self.visual_iters = visual_iters
        self.iter_count = 0
        self.jupyter=jupyter
        self.img_gen_vis = ImageGenVisualizer()
        self.stats_vis = WganTrainerStatsVisualizer()
        self.graph_vis = ModelGraphVisualizer()
        self.trainer = trainer

    def train_begin_hook(self):
        ds = self.trainer.md.val_ds 
        self.graph_vis.write_model_graph_to_tensorboard(ds=ds, model=self.trainer.netD, tbwriter=self.tbwriter) 
        self.graph_vis.write_model_graph_to_tensorboard(ds=ds, model=self.trainer.netG, tbwriter=self.tbwriter) 

    def train_loop_hook(self, gresult: WGANGenTrainingResult, cresult: WGANCriticTrainingResult): 
        self.iter_count += 1
        if self.iter_count % self.stats_iters == 0:
            self.stats_vis.print_stats_in_jupyter(gresult, cresult)
            self.stats_vis.write_tensorboard_stats(gresult, cresult, iter_count=self.iter_count, tbwriter=self.tbwriter) 

        if self.iter_count % self.visual_iters == 0:
            ds = self.trainer.md.val_ds
            model = self.trainer.netG
            self.img_gen_vis.output_image_gen_visuals(ds=ds, model=model, iter_count=self.iter_count, tbwriter=self.tbwriter, jupyter=self.jupyter)

    def close(self):
        self.tbwriter.close()
        for hook in self.hooks:
            hook.remove()


class ModelVisualizationCallback(Callback):
    def __init__(self, base_dir: Path, model: nn.Module,  md: ModelData, name: str, stats_iters: int=25, visual_iters: int=200, jupyter:bool=False):
        super().__init__()
        self.base_dir = base_dir
        self.name = name
        log_dir = base_dir/name
        clear_directory(log_dir) 
        self.tbwriter = SummaryWriter(log_dir=str(log_dir))
        self.stats_iters = stats_iters
        self.visual_iters = visual_iters
        self.iter_count = 0
        self.model = model
        self.md = md
        self.jupyter = jupyter
        self.learner_vis = LearnerStatsVisualizer()
        self.graph_vis = ModelGraphVisualizer()

    def on_train_begin(self):
        self.output_model_graph()

    def on_batch_begin(self):
        return
        
    def on_phase_begin(self):
        return

    def on_epoch_end(self, metrics):
        self.output_stats(metrics=metrics)     

    def on_phase_end(self):
        return

    def on_batch_end(self, metrics):
        self.iter_count += 1

        if self.iter_count % self.stats_iters == 0:
            self.output_stats(metrics=metrics)

        if self.iter_count % self.visual_iters == 0:
            self.output_visuals()

    def on_train_end(self):
        return

    def output_model_graph(self):
        self.graph_vis.write_model_graph_to_tensorboard(ds=self.md.val_ds, model=self.model, tbwriter=self.tbwriter)

    def output_stats(self, metrics):
        self.learner_vis.write_tensorboard_stats(metrics=metrics, iter_count=self.iter_count, tbwriter=self.tbwriter) 

    def output_visuals(self):
        self.img_gen_vis.output_image_gen_visuals(ds=self.md.val_ds, model=self.model, iter_count=self.iter_count, 
                tbwriter=self.tbwriter, jupyter=self.jupyter)
    
    def close(self):
        self.tbwriter.close()

class ImageGenVisualizationCallback(ModelVisualizationCallback):
    def __init__(self, base_dir: Path, model: nn.Module,  md: ImageData, name: str, stats_iters: int=25, visual_iters: int=200, jupyter:bool=False):
        super().__init__(base_dir=base_dir, model=model,  md=md, name=name, stats_iters=stats_iters, visual_iters=visual_iters, jupyter=jupyter)
        self.img_gen_vis = ImageGenVisualizer()

    def output_visuals(self):
        super().output_visuals()
        self.img_gen_vis.output_image_gen_visuals(ds=self.md.val_ds, model=self.model, iter_count=self.iter_count, 
                tbwriter=self.tbwriter, jupyter=self.jupyter)