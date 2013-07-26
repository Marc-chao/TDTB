import numpy as np
import make_matrix as mm
import make_matrix_graphene as mmg
import make_matrix_graphene_armchair_5nn as mmg_a
import potential
import copy
import matplotlib.pylab as plt
import scipy.sparse
from scipy.sparse import linalg
#from scipy.sparse import linalg
#from scipy import sparse

def FermiFunction(x, mu, kT):
    return 1./(1. + np.exp((x - mu).real/kT))


class GeneralHamiltonian:

    def __init__(self, mtot=None, Nx=None, Ny=None, coords=None):
        
        self.mtot = mtot
        self.Nx = Nx
        self.Ny = Ny
        
        try:
            self.Ntot = Nx * Ny
        except:
            self.Ntot = None
        self.coords = coords
        self.w = None
        self.v = None
        
    def copy_ins(self, mt, Ny = None):
        ins = copy.copy(self)
        ins.mtot = mt
        if Ny != None:
            ins.Ny = Ny
        return ins
    
    def apply_potential(self, U, sign_variation=False):
        """
        This function apply potential to the hamiltonian
        
        U: potential, an instance of Potential1D or Potential2D type
        
        The applied potential adds to the diagonal elements of the 
        hamiltonian. 
        """
        if not isinstance(U, potential.Potential1D):
            if not isinstance(U, potential.Potential2D):
                if not isinstance(U, potential.SoftConfinmentPotential):
                    if not isinstance(U, potential.SuperLatticePotential):
                        raise TypeError("f has to be instance of Potential1D or Potential2D or SoftConfinmentPotential or SuperLatticePotential")
            
        mt = self.mtot.copy()
        
        if isinstance(U, potential.Potential1D):
            
            mdia = scipy.sparse.dia_matrix((np.array([U(self.coords[i][1])
                                for i in xrange(self.Ntot)]), np.array([0])),
                                           shape=(self.Ntot,self.Ntot))
            mt = mt + mdia.tocsr()
            
        else:
            
            mdia = np.array([U([self.coords[i][0], self.coords[i][1]])
                                for i in xrange(self.Ntot)])
            
            if sign_variation:
                mdia[::2] = -1.0 * mdia[::2]
            
            mdia = scipy.sparse.dia_matrix((mdia, np.array([0])), shape=(self.Ntot,self.Ntot))
            
            mt = mt + mdia.tocsr()
            
        return self.copy_ins(mt)
    
    def apply_vector_potential(self, A):
        """
        The function applies a vector potential to the hamiltonian
        
        conversion_factor = e/h * Angstrem   is a prefactor (for graphene 1.6 * 10**5)
        
        A: a vector potential of the form [Ax, Ay]
        """
        
        #TODO: implement vector potential A(r) position dependent 
        conversion_factor = 1.602176487 / 1.0545717*1e5 
        
        nonzero_elements = self.mtot.nonzero()
        
        phase_matrix = np.exp(1j * conversion_factor * A[0] * 
                             np.array([self.coords[nonzero_elements[1][k]][0] -
                                       self.coords[nonzero_elements[0][k]][0]
                                       for k in xrange(len(nonzero_elements[0]))]))*\
                      np.exp(1j * conversion_factor * A[1] * 
                             np.array([self.coords[nonzero_elements[1][k]][1] -
                                       self.coords[nonzero_elements[0][k]][1]
                                       for k in xrange(len(nonzero_elements[0]))]))
        m_pot_data = self.mtot.data * phase_matrix
        m_pot = scipy.sparse.csr_matrix((m_pot_data, nonzero_elements), shape=(self.Ntot, self.Ntot))
        
        return self.copy_ins(m_pot)
    
    def apply_magnetic_field(self, magnetic_B=0, gauge='landau_x'):
        
        conversion_factor=1.602176487/1.0545717*1e-5  # e/hbar*Angstrem^2
        
        nonzero_elements = self.mtot.nonzero()
        
        if gauge == 'landau_x':
            phase_matrix = np.exp(1j * conversion_factor * magnetic_B * 
                                  np.array([-0.5 * (self.coords[nonzero_elements[1][k]][0] -
                                                     self.coords[nonzero_elements[0][k]][0]) *\
                                             (self.coords[nonzero_elements[0][k]][1] +
                                               self.coords[nonzero_elements[1][k]][1]) 
                                             for k in xrange(len(nonzero_elements[0]))]))
        elif gauge == 'landau_y':
            phase_matrix = np.exp(1j * conversion_factor * magnetic_B * 
                                  np.array([0.5 * (self.coords[nonzero_elements[1][k]][0] +
                                                    self.coords[nonzero_elements[0][k]][0]) *\
                                             (self.coords[nonzero_elements[1][k]][1] -
                                               self.coords[nonzero_elements[0][k]][1]) 
                                              for k in xrange(len(nonzero_elements[0]))]))
        
        m_pot_data = self.mtot.data * phase_matrix
        m_pot = scipy.sparse.csr_matrix((m_pot_data, nonzero_elements), shape=(self.Ntot, self.Ntot))
        
        return self.copy_ins(m_pot)
                    
    def eigenvalue_problem(self, k=20, sigma=0.0, **kwrds):
        w,v = linalg.eigs(self.mtot.tocsc(), k=k, sigma=sigma, **kwrds)
        return w, v
    
    def sorted_eigenvalue_problem(self, k=20, sigma=0.0, **kwrds):
        w,v = linalg.eigs(self.mtot.tocsc(), k=k, sigma=sigma, **kwrds)
        isort = np.argsort(w)
        v = np.array(v)
        wsort = np.sort(w)
        vsort = np.zeros(v.shape, dtype=complex)
        for i in xrange(len(isort)):
            vsort[:,i] = v[:,isort[i]]
        return wsort, vsort
    
    def electron_density(self, mu, kT):
        
        if self.w == None:
            self.w, self.v = self.eigenvalue_problem()
        
        rho = FermiFunction(self.w, mu, kT)
        rho2 = np.dot(self.v, np.dot(
                      np.diag(rho) * np.identity((self.Ny * self.Nx),dtype = float), 
                      np.conjugate(np.transpose(self.v))))
        
        print np.trace(rho2)
        density = np.diag(rho2)
                    
        return density
    
    def get_spec(self, k0):
        
        mlil = self.mtot.tolil()
        m0 = mlil[:self.Ny,:self.Ny].tocsr()
        mI = mlil[:self.Ny,self.Ny:2*self.Ny].tocsr()
        mIT = mI.transpose() #mlil[self.Ny:2*self.Ny,:self.Ny].tocsr()
        
        #print 'mI', mI
        #print 'mIT', mIT.transpose()
         
        dz = self.coords[self.Ny][0] - self.coords[0][0]
        dz = 1.4*np.sqrt(3.)
        A = m0 + np.exp(1j * k0 * dz) * mI +\
            np.exp(-1j * k0 * dz) * mIT
        #w, v = np.linalg.eig(A)
        n_eigs = 40
        if m0.shape[0] < n_eigs:
            n_eigs = m0.shape[0]-2
        
        w,v = linalg.eigs(A.tocsc(), k=n_eigs, sigma=0)
        wE = self.__sort_spec(w, v)[0]
        
        return wE
    
    def __sort_spec(self, w, v):
        index = np.argsort(w)
        ws = np.sort(w)
   
        #vtmp = np.zeros((len(v[:][0]), len(v[0,:])), dtype = complex)
        vtmp = []
        for i in xrange(len(index)):
            vtmp.append(v[index[i]])
   
        return ws, np.array(vtmp)
    
    def plot_bandstructure(self, krange = np.linspace(0.0,2.5,100), **kwrds):
        w = np.array([self.get_spec(k) for k in krange])
        
        [plt.plot(krange, w[:,i], **kwrds) for i in xrange(len(w[0,:]))]
        #[plt.axhline(y = np.sign(n) * np.sqrt(2. * 1.6 * 10**(-19) * 
        #                                      1.05 * 10**(-34) * 0.82**2 * 
        #                                      10**12 * 300 * np.abs(n))/1.6*10**(19)) for n in range(-6,7)]
        #plt.ylim(-1.5, 1.5)
        plt.xlabel(r'$k_x$')
        plt.ylabel(r'$E,eV$')
        #plt.show()
        return None
        
    def make_periodic_x(self):
        mtot = self.mtot.copy().tolil()
        
        mtot[-self.Ny:,:self.Ny] = mtot[:self.Ny, self.Ny:2*self.Ny]
        mtot[:self.Ny, -self.Ny:] = mtot[:self.Ny, self.Ny:2*self.Ny]
        
        return self.copy_ins(mtot.tocsr()) 

# end class GeneralHamiltonian


class HamiltonianTB(GeneralHamiltonian):
   
    def __init__(self, Ny, Nx=1):
        
        GeneralHamiltonian.__init__(self)
        
        m0 = mm.make_H0(Ny)
        mI = mm.make_HI(Ny)
        
        self.mtot = mm.make_H(m0, mI, Nx)
        self.Nx = Nx
        self.Ny = Ny
        self.Ntot = self.mtot.shape[0]
        self.coords = self.get_position()
       
    def make_periodic_y(self): 
        mlil = self.mtot.tolil()
        
        m0 = mlil[:self.Ny, :self.Ny]
        mI = mlil[:self.Ny, self.Ny:2 * self.Ny]
        
        m0[0, -1] = -mm.t
        m0[-1, 0] = -mm.t
        
        mtot = mm.make_H(m0, mI, self.Nx)
       
        return self.copy_ins(mtot)
        
    def get_position(self):
        return [[i, j, 0] for i in xrange(self.Nx) for j in xrange(self.Ny)]

#end class HamiltonianTB
 

class HamiltonianGraphene(GeneralHamiltonian):
    
    def __init__(self, Ny, Nx=1):
        
        GeneralHamiltonian.__init__(self)
        
        m0 = mmg.make_H0(Ny)
        mI = mmg.make_HI(Ny)
        self.mtot = mm.make_H(m0, mI, Nx)
        self.Nx = Nx
        self.Ny = Ny
        self.Ntot = self.mtot.shape[0]
        self.coords = self.get_position()
    
    def _instance_with_new_matrix(self, mtot):
        ins = self.__class__(self.Ny, self.Nx)
        ins.mtot = mtot
        return ins 
     
    def get_position(self):
                    
        coords = [self.__calculate_coords_in_slice(j) for j in xrange(self.Ny)]
        coords += [[coords[j][0] + i * mmg.dx, coords[j][1]] for i in xrange(1, self.Nx) for j in xrange(self.Ny)]
        
        return coords           
    
    def make_periodic_y(self):
        
        mist = np.mod(self.Ny, 4)
        ny = self.Ny
        if mist != 0:
            ny = self.Ny + 4 - mist
        
        m0 = mmg.make_periodic_H0(ny)
        mI = mmg.make_periodic_HI(ny)
        
        mtot = mm.make_H(m0, mI, self.Nx)
        
        return self.copy_ins(mtot, ny)
        
    def __calculate_coords_in_slice(self, j):
        jn = int(j)/4
        if np.mod(j,4.) == 1.0:
            return [np.sqrt(3)/2.*mmg.a, 3.*mmg.a*jn + 1./2.*mmg.a]
        elif np.mod(j, 4.) == 2.0:
            return [np.sqrt(3)/2.*mmg.a, 3.*mmg.a*jn + 3./2.*mmg.a]
        elif np.mod(j, 4.) == 3.0:
            return [0, 3.*mmg.a*jn + 2.*mmg.a]
        elif np.mod(j, 4.) == 0.0:
            return [0, 3*mmg.a*jn]    

# end class HamiltonianGraphene        

class HamiltonianGrapheneArmchair(GeneralHamiltonian):
    
    def __init__(self, Ny, Nx=1):
        
        GeneralHamiltonian.__init__(self)
        
        m0 = mmg_a.make_H0(Ny)
        mI = mmg_a.make_HI(Ny)
        self.mtot = mm.make_H(m0, mI, Nx)
        self.Nx = Nx
        self.Ny = Ny
        self.Ntot = self.mtot.shape[0]
        self.coords = self.get_position()
    
    def _instance_with_new_matrix(self, mtot):
        ins = self.__class__(self.Ny, self.Nx)
        ins.mtot = mtot
        return ins 
     
    def get_position(self):
                    
        coords = [self.__calculate_coords_in_slice(j) for j in xrange(self.Ny)]
        coords += [[coords[j][0] + i * mmg_a.dx, coords[j][1]] for i in xrange(1, self.Nx) for j in xrange(self.Ny)]
        
        return coords           
    
    '''def make_periodic_y(self):
        
        mist = np.mod(self.Ny, 4)
        ny = self.Ny
        if mist != 0:
            ny = self.Ny + 4 - mist           
        
        m0 = mmg.make_periodic_H0(ny)
        mI = mmg.make_periodic_HI(ny)
        
        mtot = mm.make_H(m0, mI, self.Nx)
        
        return self.copy_ins(mtot, ny)'''
        
    def __calculate_coords_in_slice(self, j):
        
        jn = int(j) / 2
        
        if j < self.Ny/2:
            if np.mod(j, 2.) == 0.0:
                return [0.0, np.sqrt(3)/2. * mmg_a.a * j]
            else:
                return [mmg_a.a / 2., np.sqrt(3)/2. * mmg_a.a * j]
        else:
                        
            if np.mod(j - self.Ny / 2, 2.) == 0.0:
                return [3 * mmg_a.a / 2., np.sqrt(3)/2. * mmg_a.a * (self.Ny - j - 1)]
            else:
                return [2. * mmg_a.a, np.sqrt(3)/2. * mmg_a.a * (self.Ny - j - 1)]
       
# end class HamiltonianGrapheneArmchair 


class HamiltonianFromW90(GeneralHamiltonian):
    
    def __init__(self, HamW90, Nx):
        
        GeneralHamiltonian.__init__(self)
               
        self.mtot = HamW90.maincell_hamiltonian_matrix().tocsr()
        self.coords = HamW90.orbitalpositions()       
        self.Nx = Nx
        self.Ny = self.mtot.shape[0] / Nx

        if np.mod(self.mtot.shape[0], Nx) != 0:
            self.Ny += 1
        self.Ntot = self.mtot.shape[0]

# end class HamiltonianFromW90
