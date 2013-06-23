import envtb.ldos.hamiltonian
import numpy as np
import matplotlib.pylab as plt
import envtb.time_propagator.lanczos
import envtb.time_propagator.wave_function
import envtb.time_propagator.vector_potential

directory = '/tmp/'
dt = 0.004 * 10**(-12)
NK = 12
laser_freq = 10**(12)
laser_amp = 0.5 * 10**(-2)
Nc = 3 #number of laser cycles
CEP = np.pi/2.
direct = [np.sqrt(3.)/2.,0.5]

def propagate_wave_function(wf_init, hamilt, NK=10, dt=1., maxel=None,
                            num_error=10**(-18), regime='SIL', 
                            file_out='/tmp/a.png'):
    
    prop = envtb.time_propagator.lanczos.LanczosPropagator(
        wf=wf_init, ham=hamilt, NK=NK, dt=dt)
    
    wf_final, dt_new, NK_new = prop.propagate(
        num_error=num_error, regime=regime)
    
    print 'dt_old = %(dt)g; dt_new = %(dt_new)g; NK_old = %(NK)g; NK_new = %(NK_new)g'\
            % vars()
    print 'norm', wf_final.check_norm()
    
    wf_final.plot_wave_function(maxel)
    plt.axes().set_aspect('equal')
    #plt.ylim(-100,100)
    plt.savefig(file_out)
    plt.close()
    
    #envtb.ldos.plotter.Plotter(xval=range(len(wf_final.wf1d)), yval=np.abs(wf_final.wf1d)).plotting()
    #plt.savefig(file_out+'_new.png')
    
    return wf_final, dt_new, NK_new

def propagate_graphene_pulse(Nx=30, Ny=30, frame_num=1500):
    """
    Since in lanczos in the exponent exp(E*t/hbar) we are using E in eV
    """
    ham = envtb.ldos.hamiltonian.HamiltonianGraphene(Nx, Ny)
    #ham = envtb.ldos.hamiltonian.HamiltonianTB(Nx,Ny)
    w, v = ham.eigenvalue_problem()
    isort = np.argsort(w)
    
    wsort = np.sort(w)
    vsort = np.zeros(v.shape, dtype=complex)
    for i in xrange(len(isort)):
        vsort[:,i] = v[:,isort[i]]
        
    plt.subplot(1,2,1)
    plt.plot(w.real, 'o', ms=2)
    plt.subplot(1,2,2)
    plt.plot(wsort.real, 'o', ms=2)
    plt.show()
    
    Nstate = 474
    
    envtb.ldos.plotter.Plotter().plot_density(
        vector=abs(v[:, Nstate]), coords=ham.coords)
    plt.show()
    
    # Make vector potential
    Ax = envtb.time_propagator.vector_potential.LP_SinSqEnvelopePulse(
        amplitude_E0=laser_amp, frequency=laser_freq, Nc=Nc, cep=CEP, direction=direct)
    Ax.plot_pulse()
    Ax.plot_envelope()
    Ax.plot_electric_field()
    plt.show()
    
    #main loop
    wf_out = open('wave_functions.out','w')
    dt_new = dt
    NK_new = NK
    time = 0.0
    
    wf_final = envtb.time_propagator.wave_function.WaveFunction(vec=v[:, Nstate],coords=ham.coords)
    maxel = max(wf_final.wf1d)
    wf_out.writelines(`time`+'   '+`wf_final.wf1d.tolist()`+'\n')
    
    
    for i in xrange(5500):
        print 'frame %(i)d' % vars()
        time += dt_new
        ham2 = ham.apply_vector_potential(Ax(time))
        print 'time', time, 'A', Ax(time)
        wf_init = wf_final
        wf_final, dt_new, NK_new = propagate_wave_function(
            wf_init, ham2, NK=NK_new, dt=dt_new, 
            maxel = maxel, regime='TSC', 
            file_out = directory+'f%03d_2d.png' % i)
        
        if np.mod(i,10) == 0:
            wf_out.writelines(`time`+'   '+`wf_final.wf1d.tolist()`+'\n')
           
    wf_out.close()

propagate_graphene_pulse()
